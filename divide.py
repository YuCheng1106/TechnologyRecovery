import mysql.connector
import time

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'liweiran',
    'database': 'technologyrecovery',
    'charset': 'utf8mb4',
    'autocommit': True
}

def connect_to_db():
    """连接到MySQL数据库"""
    try:
        db = mysql.connector.connect(**DB_CONFIG)
        cursor = db.cursor()
        print("成功连接到数据库")
        return db, cursor
    except mysql.connector.Error as err:
        print(f"连接数据库失败: {err}")
        exit(1)

def split_text_by_double_newlines(text):
    """按双换行符分割文本"""
    parts = []
    current_part = []

    for line in text.splitlines():
        if line.strip() == '' and current_part:
            parts.append('\n'.join(current_part))
            current_part = []
        else:
            current_part.append(line)

    if current_part:
        parts.append('\n'.join(current_part))

    return parts

def insert_log_parts(text):
    """将分割后的日志部分插入数据库"""
    db, cursor = connect_to_db()
    parts = split_text_by_double_newlines(text)

    for i, part in enumerate(parts, start=1):
        retries = 0
        max_retries = 2

        while retries <= max_retries:
            try:
                # 插入数据到MySQL
                query = "INSERT INTO worklog (工作日志) VALUES (%s)"
                cursor.execute(query, (part,))
                db.commit()
                print(f"部分{i}日志数据已成功插入到数据库")
                break  # 跳出重试循环
            except mysql.connector.Error as err:
                retries += 1
                if retries > max_retries:
                    print(f"插入部分{i}数据失败: {err}")
                    break  # 跳过该部分，继续下一部分
                print(f"重试插入部分{i}数据...")
                time.sleep(5)  # 等待5秒后重试

    cursor.close()
    db.close()

# 主框架调用示例
def divide(text):
    try:
        insert_log_parts(text)
        return True
    except Exception as e:
        print(f"处理时发生错误: {str(e)}")
        return False

