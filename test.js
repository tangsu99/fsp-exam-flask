const testQuestions1 = [
    {
        id: 1,
        type: "singleChoice",
        title: "附魔金苹果可以合成吗",
        options: ["可以", "不可以"],
        score: 5,
        answer: "B",
    },
    {
        id: 2,
        type: "singleChoice",
        title: "末地烛可以合成吗",
        options: ["可以", "不可以"],
        score: 5,
        answer: "A",
    },
    {
        id: 3,
        type: "singleChoice",
        title: "伪和平可以防止幻翼生成吗",
        options: ["可以", "不可以"],
        score: 5,
        answer: "B",
    },
    
    {
        id: 20,
        type: "fillInTheBlanks",
        title: "活塞最多可推动多少个方块",
        score: 10,
        answer: "12",
    },
    {
        id: 21,
        type: "fillInTheBlanks",
        title: "红石中继器有几个延迟档位",
        score: 10,
        answer: "4",
    },
    {
        id: 22,
        type: "fillInTheBlanks",
        title: "(4961+56-17)÷5 等于几",
        score: 10,
        answer: "1000",
    },
    {
        id: 23,
        type: "subjective",
        title: "图1 工作台切换装置，图2 拉下拉杆，图3 装置背面，图4 装置侧面，图5中是否可以去掉红框内的红石粉，如果不可以，请简述为什么",
        img_url: [
            "./images/23-1.png",
            "./images/23-2.png",
            "./images/23-3.png",
            "./images/23-4.png",
            "./images/23-5.png",
        ],
        score: 10,
    },
    {
        id: 24,
        type: "subjective",
        score: 10,
        title: "已知主世界中有地狱门，坐标看成一个单点\n1.在地狱(0,0)建造地狱门，求主世界地狱门串门和生成地狱门范围\n2.现已知主世界地狱门有两扇地狱门串门，其单点坐标一致，朝向一致，高度差为40格，其中y（A）＞y（B），求地狱门串门所有可能",
    },
    {
        id: 25,
        type: "subjective",
        score: 10,
        title: "比较器在减法模式有容器检测的情况下 用侦测器瞬息中继器的直出时序是几gt并解释原因",
        answer: "答案：2gt,这里比较器被侦测器瞬息减法模式可以减去2gt的响应时间(比较器特性)，所以只有中继器有延迟，中继器一档有2gt延迟",
    }
]