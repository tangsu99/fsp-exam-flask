#!/usr/bin/env python3
"""
数据库结构同步工具

比较两个 MySQL 数据库的 DDL 差异，生成从源库同步到目标库的 SQL 语句。

用法:
    python scripts/sync_db_schema.py --source user:pass@host:port/db --target user:pass@host:port/db
    python scripts/sync_db_schema.py --source-dump source.sql --target-dump target.sql
    python scripts/sync_db_schema.py --help
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


def dump_ddl(conn_str: str, output: str) -> None:
    """执行 mysqldump 导出表结构"""
    # 解析连接字符串 user:pass@host:port/db
    import urllib.parse

    if ":" in conn_str and "@" in conn_str:
        user_pass, rest = conn_str.split("@", 1)
        user, password = user_pass.split(":", 1) if ":" in user_pass else (user_pass, "")
        host_port, db = rest.split("/", 1) if "/" in rest else (rest, "")
        host = host_port
        port = "3306"
        if ":" in host_port:
            host, port = host_port.split(":", 1)
    else:
        # 尝试解析为标准 URL
        parsed = urllib.parse.urlparse(conn_str)
        user = parsed.username or "root"
        password = parsed.password or ""
        host = parsed.hostname or "localhost"
        port = str(parsed.port or 3306)
        db = parsed.path.lstrip("/")

    cmd = [
        "mysqldump",
        "-u",
        user,
        f"-p{password}" if password else "",
        "-h",
        host,
        "-P",
        port,
        "--no-data",
        "--routines",
        "--triggers",
        db,
    ]
    cmd = [c for c in cmd if c]

    print(f"  导出 {db} 的 DDL ...", file=sys.stderr)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ❌ mysqldump 失败: {result.stderr}", file=sys.stderr)
        # 尝试交互式输入密码
        if "password" in result.stderr.lower():
            cmd_no_pw = [c for c in cmd if not c.startswith("-p")]
            print("  尝试交互式输入密码 ...", file=sys.stderr)
            subprocess.run(cmd_no_pw, stdout=open(output, "w"))
            return

        sys.exit(1)

    with open(output, "w", encoding="utf-8") as f:
        f.write(result.stdout)
    print(f"  ✅ 已保存到 {output}", file=sys.stderr)


def parse_tables(ddl_text: str) -> dict[str, str]:
    """从 DDL 文本中提取所有 CREATE TABLE 语句"""
    pattern = r"(CREATE TABLE `(\w+)` \(.*?\) ENGINE[^;]+;)"
    return {m[1]: m[0] for m in re.findall(pattern, ddl_text, re.DOTALL)}


def extract_columns(ddl: str) -> dict[str, str]:
    """提取表中的列定义（排除索引、约束等）"""
    body = ddl[ddl.index("(") + 1 : ddl.rindex(")")]
    result: dict[str, str] = {}
    for line in body.split(",\n"):
        line = line.strip().rstrip(",")
        if not line:
            continue
        if re.match(
            r"^(KEY |PRIMARY KEY|CONSTRAINT|UNIQUE KEY|INDEX|FULLTEXT|SPATIAL)",
            line,
        ):
            continue
        m = re.match(r"`(\w+)`\s+(.*)", line)
        if m:
            result[m.group(1)] = m.group(2).strip().rstrip(",")
    return result


def extract_indexes(ddl: str) -> list[str]:
    """提取索引和约束定义"""
    body = ddl[ddl.index("(") + 1 : ddl.rindex(")")]
    result: list[str] = []
    for line in body.split(",\n"):
        line = line.strip().rstrip(",")
        if not line:
            continue
        if re.match(
            r"^(KEY |PRIMARY KEY|CONSTRAINT|UNIQUE KEY|INDEX|FULLTEXT|SPATIAL)",
            line,
        ):
            result.append(line)
    return result


def compare(source_file: str, target_file: str) -> str:
    """比较两个 DDL 文件，返回同步 SQL"""
    with open(source_file, encoding="utf-8") as f:
        source_ddl = f.read()
    with open(target_file, encoding="utf-8") as f:
        target_ddl = f.read()

    src_tables = parse_tables(source_ddl)
    tgt_tables = parse_tables(target_ddl)

    output: list[str] = []
    output.append("-- =============================================")
    output.append("-- 数据库结构同步 SQL")
    output.append(f"-- 源库: {source_file}")
    output.append(f"-- 目标库: {target_file}")
    output.append(f"-- 生成时间: {__import__('datetime').datetime.now()}")
    output.append("-- =============================================")
    output.append("")

    # ---- 1. 新建表 ----
    new_tables = sorted(set(src_tables) - set(tgt_tables) - {"alembic_version"})
    if new_tables:
        output.append("-- ========== 1. 新建表 ==========")
        for t in new_tables:
            # 清理 AUTO_INCREMENT 值，避免覆盖生产自增 ID
            clean_ddl = re.sub(r"AUTO_INCREMENT=\d+", "AUTO_INCREMENT=1", src_tables[t])
            output.append(clean_ddl)
            output.append("")

    # ---- 2. 列差异 ----
    common_tables = sorted(set(src_tables) & set(tgt_tables) - {"alembic_version"})
    has_column_diff = False
    for t in common_tables:
        src_cols = extract_columns(src_tables[t])
        tgt_cols = extract_columns(tgt_tables[t])

        for col in sorted(src_cols):
            if col not in tgt_cols:
                if not has_column_diff:
                    output.append("-- ========== 2. 新增/修改列 ==========")
                    has_column_diff = True
                output.append(f"ALTER TABLE `{t}` ADD COLUMN `{col}` {src_cols[col]};")
            elif src_cols[col] != tgt_cols[col]:
                if not has_column_diff:
                    output.append("-- ========== 2. 新增/修改列 ==========")
                    has_column_diff = True
                output.append(f"ALTER TABLE `{t}` MODIFY COLUMN `{col}` {src_cols[col]};")

    # ---- 3. 索引差异 ----
    has_idx_diff = False
    for t in common_tables:
        src_idx = extract_indexes(src_tables[t])
        tgt_idx = extract_indexes(tgt_tables[t])

        # 找出源库有但目标库没有的索引
        for idx in src_idx:
            if idx not in tgt_idx:
                if not has_idx_diff:
                    output.append("")
                    output.append("-- ========== 3. 新增索引/约束 ==========")
                    has_idx_diff = True
                # 提取索引名和类型
                m_key = re.match(r"(KEY|UNIQUE KEY|CONSTRAINT)\s+`?(\w+)`?", idx)
                if m_key:
                    kw = m_key.group(1)
                    name = m_key.group(2)
                    if kw == "CONSTRAINT":
                        # 外键约束，从原 DDL 提取
                        ref_match = re.search(r"REFERENCES\s*`?(\w+)`?\s*\(`?(\w+)`?\)", idx)
                        on_delete = re.search(r"ON DELETE (\w+)", idx)
                        if ref_match:
                            ref_table = ref_match.group(1)
                            ref_col = ref_match.group(2)
                            fk_col_match = re.search(r"FOREIGN KEY\s*\(`?(\w+)`?\)", idx)
                            fk_col = fk_col_match.group(1) if fk_col_match else ""
                            sql = (
                                f"ALTER TABLE `{t}` ADD CONSTRAINT `{name}` FOREIGN KEY (`{fk_col}`) "
                                f"REFERENCES `{ref_table}` (`{ref_col}`)"
                            )
                            if on_delete:
                                sql += f" ON DELETE {on_delete.group(1)}"
                            sql += ";"
                            output.append(sql)
                    else:
                        # 普通索引/唯一索引
                        col_match = re.search(r"\(`?(\w+)`?\)", idx)
                        if col_match:
                            col = col_match.group(1)
                            if kw == "UNIQUE KEY":
                                output.append(f"ALTER TABLE `{t}` ADD UNIQUE INDEX `{name}` (`{col}`);")
                            else:
                                output.append(f"CREATE INDEX `{name}` ON `{t}` (`{col}`);")

    # ---- 4. 仅在目标库中的多余表 ----
    extra_tables = sorted(set(tgt_tables) - set(src_tables) - {"alembic_version"})
    if extra_tables:
        output.append("")
        output.append("-- ========== 4. ⚠️ 目标库多余表（请手动确认是否删除） ==========")
        for t in extra_tables:
            output.append(f"-- DROP TABLE IF EXISTS `{t}`;  -- 目标库多余")

    output.append("")
    output.append("-- =============================================")
    output.append("-- 同步 SQL 生成完毕，请审阅后再执行")
    output.append("-- =============================================")

    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(
        description="比较两个 MySQL 数据库的结构差异，生成同步 SQL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 方式 1: 直接连接数据库（自动导出 DDL）
  python scripts/sync_db_schema.py \\
      --source root:pass@localhost:3306/dev_db \\
      --target root:pass@prod_host:3306/prod_db

  # 方式 2: 使用已导出的 DDL 文件
  python scripts/sync_db_schema.py \\
      --source-dump dev_ddl.sql \\
      --target-dump prod_ddl.sql

  # 方式 3: 仅导出 DDL
  python scripts/sync_db_schema.py --dump-only root:pass@host:3306/db
        """,
    )

    group = parser.add_argument_group("连接方式（二选一）")
    group.add_argument(
        "--source",
        help="源库连接字符串，格式: user:password@host:port/database",
    )
    group.add_argument(
        "--target",
        help="目标库连接字符串，格式: user:password@host:port/database",
    )

    group2 = parser.add_argument_group("或使用已导出的 DDL 文件")
    group2.add_argument("--source-dump", help="源库 DDL 文件路径")
    group2.add_argument("--target-dump", help="目标库 DDL 文件路径")

    parser.add_argument("--dump-only", help="仅导出指定库的 DDL，不比较")
    parser.add_argument("-o", "--output", help="输出 SQL 文件路径（默认输出到终端）")

    args = parser.parse_args()

    # ---- 仅导出 DDL ----
    if args.dump_only:
        output_file = f"{args.dump_only.replace('/', '_').replace(':', '_')}_ddl.sql"
        dump_ddl(args.dump_only, output_file)
        print(f"\nDDL 已导出到: {output_file}")
        return

    # ---- 获取 DDL 文件 ----
    source_file = args.source_dump
    target_file = args.target_dump

    tmp_dir = Path("_ddl_cache")

    if args.source and args.target:
        # 自动导出 DDL
        tmp_dir.mkdir(exist_ok=True)

        source_file = str(tmp_dir / "source_ddl.sql")
        target_file = str(tmp_dir / "target_ddl.sql")

        print("正在导出源库 DDL ...")
        dump_ddl(args.source, source_file)
        print("正在导出目标库 DDL ...")
        dump_ddl(args.target, target_file)
        print()

    if not source_file or not target_file:
        parser.print_help()
        print("\n❌ 请提供 --source/--target 或 --source-dump/--target-dump", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(source_file):
        print(f"❌ 找不到源库 DDL 文件: {source_file}", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(target_file):
        print(f"❌ 找不到目标库 DDL 文件: {target_file}", file=sys.stderr)
        sys.exit(1)

    # ---- 比较 ----
    print("正在比较 DDL 差异 ...", file=sys.stderr)
    result = compare(source_file, target_file)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"\n✅ 同步 SQL 已保存到: {args.output}", file=sys.stderr)
        print(f"   请审阅 {args.output} 后再在目标库执行", file=sys.stderr)
    else:
        print("\n" + "=" * 60)
        print(result)

    # 清理缓存
    if args.source and args.target:
        for f in [source_file, target_file]:
            if os.path.exists(f):
                os.remove(f)
        rmdir = tmp_dir
        if not any(rmdir.iterdir()):
            rmdir.rmdir()


if __name__ == "__main__":
    main()
