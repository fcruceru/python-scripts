from datetime import datetime
from difflib import SequenceMatcher
import os

LIST_OF_MESSAGES = []
UNIQUE_MESSAGES = []
SIMILARITY_RATIO = 0.8
LOG_FILES = ["logs/log1.log", "logs/log1.log", "logs/log3.log"]


def check_message_similarity(msg1, msg2):
    s = SequenceMatcher(None, msg1.message, msg2.message)
    if msg1.class_name == msg2.class_name:
        if s.ratio() > SIMILARITY_RATIO:
            return True
    return False


def write_to_file(file_name):
    if not os.path.exists('output'):
        os.makedirs('output')
    file_name = file_name[5:-3]
    file_path = 'output/' + 'sorted_' + file_name + "txt"
    with open(file_path, 'w') as file:
        for item in UNIQUE_MESSAGES:
            file.write(str(item.occurrences) + " " + item.class_name + " - " + item.message)


def sort_messages():
    print("Number of messages is %d" % len(LIST_OF_MESSAGES))
    while len(LIST_OF_MESSAGES) > 1:  # not empty
        current = 1
        while current < len(LIST_OF_MESSAGES):
            if current > len(LIST_OF_MESSAGES) - 1:
                break
            if check_message_similarity(LIST_OF_MESSAGES[0], LIST_OF_MESSAGES[current]):
                LIST_OF_MESSAGES[0].occurrences += 1
                LIST_OF_MESSAGES.pop(current)
                current -= 1
            current += 1
        UNIQUE_MESSAGES.append(LIST_OF_MESSAGES[0])
        LIST_OF_MESSAGES.pop(0)
    UNIQUE_MESSAGES.append(LIST_OF_MESSAGES[0])
    print("Number of unique messages is %d" % len(UNIQUE_MESSAGES))


def parse_line(line):
    line = line[+24:]
    thread = line[+1:line.find("]")]
    debug_level = line[len(thread) + 3:line.find(" c.") - 1]
    class_name = line[line.find("c."):line.find(" -")]
    if debug_level == "INFO":
        message = line[line.find("- ") + 2:]
        LIST_OF_MESSAGES.append(LogMessage(class_name, message, 1))


def parse_logfile(file_name):
    exception_lines = 0
    with open(file_name) as file:
        data = file.readlines()
    for line in data:
        if line.startswith("2020"):  # Ignore exceptions
            parse_line(line)
        else:
            exception_lines += 1
    sort_messages()
    write_to_file(file_name)
    print("Finished parsing log file.")
    print("Number of exception lines found: %d" % exception_lines)


def main():
    # TODO: when parsing line, decide whether to put it in list of messages or not, don't go over it twice
    start_time = datetime.now()
    print("Started script at %s" % start_time)
    for log in LOG_FILES:
        print("Parsing log file: %s" % log)
        parse_logfile(log)
    end_time = datetime.now()
    print("Finished script at %s" % end_time)
    print("Script took %d seconds" % (end_time - start_time).total_seconds())


class LogMessage:
    def __init__(self, class_name, message, occurrences):
        self.class_name = class_name
        self.message = message
        self.occurrences = occurrences


main()
