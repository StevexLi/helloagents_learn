import re
import random

# 定义规则库：模式(正则表达式) -> 响应模板列表
rules_set = {
    r'My (.*) is (.*)': [
        "OK. Your {0} is {1}. Please tell me more."
    ],
    r'Forget my (.*)': [
        "OK. Your {0} info is deleted. Please tell me other things.",
        "Sorry, you didn't tell me your {0} before."
    ],
}

rules_check = {
    r"(?:What is|What is|Who is|When is|Where is) my (.*)\?": [
        "Sorry, you didn't tell me your {0} before.",
        "Your {0} is {1}."
    ],
}

rules = {
    r'I need (.*)': [
        "Why do you need {0}?",
        "Would it really help you to get {0}?",
        "Are you sure you need {0}?"
    ],
    r'Why don\'t you (.*)\?': [
        "Do you really think I don't {0}?",
        "Perhaps eventually I will {0}.",
        "Do you really want me to {0}?"
    ],
    r'Why can\'t I (.*)\?': [
        "Do you think you should be able to {0}?",
        "If you could {0}, what would you do?",
        "I don't know -- why can't you {0}?"
    ],
    r'I am (.*)': [
        "Did you come to me because you are {0}?",
        "How long have you been {0}?",
        "How do you feel about being {0}?"
    ],
    r'.* mother .*': [
        "Tell me more about your mother.",
        "What was your relationship with your mother like?",
        "How do you feel about your mother?"
    ],
    r'.* father .*': [
        "Tell me more about your father.",
        "How did your father make you feel?",
        "What has your father taught you?"
    ],
    r'I feel (.*)': [
        "Why do you feel {0}?",
        "What do you do when you feel {0}?",
        "When did you start feeling {0}?"
    ],
    r'.*': [
        "Please tell me more.",
        "Let's change focus a bit... Tell me about your family.",
        "Can you elaborate on that?"
    ],
}

# 定义一个空字典：key 和 value 都是字符串
string_dictionary: dict[str, str] = {}


def add_dictionary_entry(key: str, value: str) -> None:
    """
    向字典中添加或更新一个键值对。
    """
    string_dictionary[key] = value


def delete_dictionary_entry(key: str) -> bool:
    """
    根据 key 删除字典中的键值对。
    删除成功返回 True；key 不存在时返回 False。
    """
    if key in string_dictionary:
        del string_dictionary[key]
        return True
    return False


# 定义代词转换规则
pronoun_swap = {
    "i": "you", "you": "i", "me": "you", "my": "your",
    "am": "are", "are": "am", "was": "were", "i'd": "you would",
    "i've": "you have", "i'll": "you will", "yours": "mine",
    "mine": "yours",  "your": "my"
}



def swap_pronouns(phrase):
    """
    对输入短语中的代词进行第一/第二人称转换
    """
    words = phrase.lower().split()
    swapped_words = [pronoun_swap.get(word, word) for word in words]
    return " ".join(swapped_words)

def respond(user_input):
    """
    根据规则库生成响应
    """
    normalized_input = user_input.strip()
    if normalized_input.endswith("."):
        normalized_input = normalized_input[:-1].strip()

    for index, (pattern, responses) in enumerate(rules_set.items()):
        match = re.search(pattern, normalized_input, re.IGNORECASE)
        if not match:
            continue

        key = match.group(1).strip().lower()
        if index == 0:
            value = match.group(2).strip()
            add_dictionary_entry(key, value)
            return responses[0].format(key, value)

        if delete_dictionary_entry(key):
            return responses[0].format(key)
        return responses[1].format(key)

    for pattern, responses in rules_check.items():
        match = re.search(pattern, normalized_input, re.IGNORECASE)
        if match:
            key = match.group(1).strip().lower()
            value = string_dictionary.get(key)
            if value is None:
                return responses[0].format(key)
            return responses[1].format(key, value)

    for pattern, responses in rules.items():
        match = re.search(pattern, normalized_input, re.IGNORECASE)
        if match:
            # 捕获匹配到的部分
            captured_group = match.group(1) if match.groups() else ''
            # 进行代词转换
            swapped_group = swap_pronouns(captured_group)
            # 从模板中随机选择一个并格式化
            response = random.choice(responses).format(swapped_group)
            return response
    # 如果没有匹配任何特定规则，使用最后的通配符规则
    return random.choice(rules[r'.*'])

# 主聊天循环
if __name__ == '__main__':
    print("Therapist: Hello! How can I help you today?")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["quit", "exit", "bye"]:
            print("Therapist: Goodbye. It was nice talking to you.")
            break
        response = respond(user_input)
        print(f"Therapist: {response}")
