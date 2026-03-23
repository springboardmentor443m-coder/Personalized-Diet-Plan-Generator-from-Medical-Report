import re
import json


def extract_structured_data(text):

    data = {
        "lab_results": []
    }

    lines = text.split("\n")

    for i in range(len(lines)):

        line = lines[i].strip()

        # Pattern 1: VALUE immediately followed by test name
        match1 = re.match(r"^([\d\.]+)([A-Za-z ,()/-]+)", line)

        # Pattern 2: Test name first then value later
        match2 = re.match(r"^([A-Za-z ,()/-]+)\s+([\d\.]+)", line)

        if match1:
            value = match1.group(1)
            test_name = match1.group(2).strip()

            data["lab_results"].append({
                "test_name": test_name,
                "value": float(value)
            })

        elif match2:
            test_name = match2.group(1).strip()
            value = match2.group(2)

            data["lab_results"].append({
                "test_name": test_name,
                "value": float(value)
            })

    return data


def save_json(data, filename="output.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)