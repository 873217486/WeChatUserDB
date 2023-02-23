import base64
import json
import os
import re
import shutil
import sqlite3
import time

import connect_sqlite_tools
import get_info
import win_db_decode
from decode_img import get_code

print("\n确保微信已登录，否则聊天记录导出失败")
print("正在获取微信秘钥...")
base64pwd_wxid = get_info.get_key(0)
# base64pwd_wxid = ('05eIFhsEQ6yd4e9cJ1CxklXFtbuh80eGvEDabb8O6UM=', 'wxid_f9ncqun8hz2i22')
key = base64.standard_b64decode(base64pwd_wxid[0])
# 当前：C:\Users\Administrator\Documents\WeChat Files\
wechatFilePath = 0
# 当前：jiangshan873217486
wechatId = base64pwd_wxid[1]
print("\n获取秘钥成功", base64pwd_wxid, "\n")


def decrypt_db(dbFile):
    msgDB = wechatFilePath + wechatId + dbFile
    connect_sqlite_tools.decrypt_sqlite_file(msgDB, key)


def ex_sql(db, sql, params=()):
    conn = sqlite3.connect(db)
    c = conn.cursor()
    cursor = c.execute(sql, params)
    result = []
    for row in cursor:
        result.append(row)
    conn.close()
    return result


# 微信聊天记录很多的时候会生成多个MSG0 MSG1 MSG2.db
# 检查已经产生了多少个MSG.db
def check_count_msg_db():
    count_msg_db = 0
    while "MSG" + str(count_msg_db) + ".db" in os.listdir(wechatFilePath + wechatId + '\\Msg\\Multi\\'):
        count_msg_db += 1
    return count_msg_db


def decode_dat(file_path):
    # .\微信聊天记录导出\xxxx.dat
    copyPath = ".\\微信聊天记录导出\\" + os.path.basename(file_path)
    # xxxx.jpg
    jpgImgName = os.path.basename(file_path).replace('.dat', '.jpg')

    shutil.copyfile(file_path, copyPath)
    decode_code = get_code(copyPath)
    dat_file = open(copyPath, "rb")

    pic_write = open(".\\微信聊天记录导出\\" + jpgImgName, "wb")
    for dat_data in dat_file:
        for dat_byte in dat_data:
            pic_data = dat_byte ^ decode_code
            pic_write.write(bytes([pic_data]))
    print(jpgImgName + "解密完成")
    dat_file.close()
    pic_write.close()
    os.remove(copyPath)
    return jpgImgName


if __name__ == '__main__':
    # 1 设置微信存储位置
    print("请输入微信存储位置，在【设置】-【文件管理】")
    wechatFilePath = input("不输入时使用默认位置：C:\\Users\\Administrator\\Documents\\WeChat Files\\\n")
    if not wechatFilePath:
        wechatFilePath = "C:\\Users\\Administrator\\Documents\\WeChat Files\\"

    count_msg_db = check_count_msg_db()
    # 2 复制微信数据库
    for i in range(count_msg_db):
        decrypt_db("\\Msg\\Multi\\MSG" + str(i) + ".db")
    decrypt_db("\\Msg\\FTSContact.db")

    # 3 输入需要导出的群聊名称 默认：小台风售后退款群
    # 22431475380@chatroom
    export_group_id = ''
    while not export_group_id:
        export_group_name = input('输入需要导出的群聊名或微信名（！不是微信备注） 不输入时使用默认导出：小台风售后退款群')
        if not export_group_name:
            export_group_name = '小台风售后退款群'
        # 根据群名查询群ID：小台风售后退款群 -> 22431475380@chatroom
        sql = '''
                SELECT
                    userName 
                FROM
                    NameToId 
                    LIMIT ( SELECT entityId FROM FTSContact15_MetaData WHERE docid = ( SELECT docid FROM FTSContact15_content WHERE c1nickname = ? ) ) - 1,1
        '''
        try:
            export_group_id = ex_sql('./DECRYPT_WIN_WECHAT_DB/decrypt_copy_FTSContact.db', sql, [export_group_name])[0][
                0]
        except:
            print("没有找到该群聊或微信名\n\n")

    # 3 查询数据库 选择需要导出的聊天记录
    # sql = '''   SELECT
    #                 g.groupTalkerId AS groupTalkerId,
    #                 a.c1nickname
    #             FROM
    #                 ( SELECT groupTalkerId FROM FTSChatroom15_MetaData GROUP BY groupTalkerId ) g
    #                 LEFT JOIN FTSContact15_content a ON a.docid = g.groupTalkerId
    #             WHERE
    #                 a.c1nickname <> ''
    #                 '''
    # groupArray = ex_sql('./DECRYPT_WIN_WECHAT_DB/decrypt_copy_FTSContact.db', sql)
    # i = 1
    # print('------------------------')
    # for groupRow in groupArray:
    #     print(str(i) + "：" + groupRow[1])
    #     i = i + 1
    # print('------------------------')
    #
    # inputIndex = input("请输入数字选择群聊：\n")
    # # 327
    # groupTalkerId = groupArray[int(inputIndex) - 1][0]
    # sql = 'SELECT * from NameToId limit ' + str(groupTalkerId - 1) + ',1'
    # # 18972836328@chatroom
    # groupTalkerId = ex_sql('./DECRYPT_WIN_WECHAT_DB/decrypt_copy_FTSContact.db', sql)[0][0]

    sql = 'SELECT count(1) FROM MSG WHERE IsSender = 0 AND StrTalker = ?'
    countMsg = 0
    for i in range(count_msg_db):
        countMsg += ex_sql('./DECRYPT_WIN_WECHAT_DB/decrypt_copy_MSG' + str(i) + '.db', sql, [export_group_id])[0][0]

    start_msg_sequence = ''
    while not start_msg_sequence:
        startMsg = input("\n共找到" + str(
            countMsg) + "条聊天记录\n请输入开始导入的聊天记录(从输入的聊天记录到最新的聊天记录全部导出)：\n")
        # 查询消息开始的下标位置
        sql = '''
                    SELECT
                        MsgSequence, CreateTime
                    FROM
                        MSG 
                    WHERE
                        StrTalker = ? 
                        AND StrContent = ?
         '''
        match_msg_array = []
        for i in range(count_msg_db):
            sql_result = ex_sql('./DECRYPT_WIN_WECHAT_DB/decrypt_copy_MSG' + str(i) + '.db', sql,
                                (export_group_id, startMsg))
            match_msg_array.extend(sql_result)
        if not match_msg_array:
            print("没有查询到该条聊天记录！\n")
            continue
        print("查询到" + str(len(match_msg_array)) + "条聊天记录，请选择：")
        print('------------------------')
        i = 1
        for item in match_msg_array:
            time_local = time.localtime(item[1])
            ymd = time.strftime("%Y-%m-%d %H:%M:%S", time_local)
            print(str(i) + "：" + startMsg + " " + ymd)
            i += 1
        print('------------------------')
        input_index = input()
        start_msg_sequence = match_msg_array[int(input_index) - 1][0]
    # 查询要导出的消息
    exportMsgArray = []
    for i in range(count_msg_db):
        sql = '''   SELECT
                        Type, StrContent, BytesExtra, localId
                    FROM
                        MSG 
                    WHERE
                        StrTalker = ? 
                        AND IsSender = 0
                        AND MsgSequence >= ?'''
        sql_result = ex_sql('./DECRYPT_WIN_WECHAT_DB/decrypt_copy_MSG' + str(i) + '.db', sql,
                            (export_group_id, start_msg_sequence))
        exportMsgArray.extend(sql_result)
    print("\n已找到" + str(len(exportMsgArray)) + "条聊天记录")
    print("正在导出聊天记录...\n")
    # 数据库存储的内容
    # re.findall('FileStorage..?Image..?\d+-\d+..\w+.dat', str(exportMsg[13][2]))
    if "微信聊天记录导出" in os.listdir():
        shutil.rmtree("./微信聊天记录导出")
    os.mkdir("微信聊天记录导出")

    exportMsgJson = []
    for exportMsg in exportMsgArray:
        # xxxx.jpg
        img = ''
        msgType = exportMsg[0]
        if msgType == 1:
            content = exportMsg[1]  # 普通消息
        elif msgType == 3:
            content = ''  # 图片消息
            imgArray = re.findall('FileStorage..?Image..?\d+-\d+..\w+.dat', str(exportMsg[2]))
            if len(imgArray) == 0:
                # 新版微信聊天记录存储位置改变
                # FileStorage\\MsgAttach\\6692a9bd8ab8e263e4948262f012e586\\Image\\2023-02\\1e4685b02ee565b264025e5db5f3ba0e.dat
                imgArray = re.findall('FileStorage..?MsgAttach..?\w+..Image..?\d+-\d+..\w+.dat', str(exportMsg[2]))
            if len(imgArray) > 0:
                imgPath = imgArray[0].replace('\\\\', '\\')
                try:
                    img = decode_dat(wechatFilePath + wechatId + '\\' + imgPath)
                except:
                    content = '图片过期或已被清理或未下载原图'
                    msgType = 1
            else:
                content = '异常：未能成功导出图片'
                msgType = 1
        else:
            content = '其他消息'

        exportMsgJson.append({
            'type': msgType,
            'content': content,
            'img': img
        })
    f = open('./微信聊天记录导出/log.json', 'w', encoding='utf-8')
    f.write(json.dumps(exportMsgJson, ensure_ascii=False))
    f.close()
    print("微信聊天记录导出成功，位置：")
    print(os.getcwd() + "\\微信聊天记录导出")
    os.system('pause')
