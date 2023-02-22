import base64
import json
import os
import re
import shutil
import sqlite3

import connect_sqlite_tools
import get_info
import win_db_decode
from decode_img import get_code

print("\n确保微信已登录，否则聊天记录导出失败")
print("正在获取微信秘钥...")
base64pwd_wxid = get_info.get_key(0)
key = base64.standard_b64decode(base64pwd_wxid[0])
wechatFilePath = 0
print("\n获取秘钥成功", base64pwd_wxid, "\n")


def decrypt_db(dbFile):
    msgDB = wechatFilePath + base64pwd_wxid[1] + dbFile
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

    # 2 复制微信数据库
    decrypt_db("\\Msg\\Multi\\MSG0.db")
    decrypt_db("\\Msg\\FTSContact.db")

    # 3 查询数据库 选择需要导出的聊天记录
    sql = '''   SELECT
                    g.groupTalkerId AS groupTalkerId,
                    a.c1nickname 
                FROM
                    ( SELECT groupTalkerId FROM FTSChatroom15_MetaData GROUP BY groupTalkerId ) g
                    LEFT JOIN FTSContact15_content a ON a.docid = g.groupTalkerId 
                WHERE
                    a.c1nickname <> ''
                    '''
    groupArray = ex_sql('./DECRYPT_WIN_WECHAT_DB/decrypt_copy_FTSContact.db', sql)
    i = 1
    print('------------------------')
    for groupRow in groupArray:
        print(str(i) + "：" + groupRow[1])
        i = i + 1
    print('------------------------')

    inputIndex = input("请输入数字选择群聊：\n")
    # 327
    groupTalkerId = groupArray[int(inputIndex) - 1][0]
    sql = 'SELECT * from NameToId limit ' + str(groupTalkerId - 1) + ',1'
    # 18972836328@chatroom
    groupTalkerId = ex_sql('./DECRYPT_WIN_WECHAT_DB/decrypt_copy_FTSContact.db', sql)[0][0]

    sql = 'SELECT count(1) FROM MSG WHERE IsSender = 0 AND StrTalker = ?'
    countMsg = ex_sql('./DECRYPT_WIN_WECHAT_DB/decrypt_copy_MSG0.db', sql, [groupTalkerId])[0][0]
    startMsg = input("\n共找到" + str(countMsg) + "条聊天记录\n请输入开始导入的聊天记录(从输入的聊天记录到最新的聊天记录全部导出)：\n")
    sql = '''   SELECT
                    Type, StrContent, BytesExtra, localId
                FROM
                    MSG 
                WHERE
                    StrTalker = ? 
                    AND IsSender = 0
                    AND localId >= ( SELECT localId FROM MSG WHERE StrContent = ? AND StrTalker = ? )'''
    exportMsgArray = ex_sql('./DECRYPT_WIN_WECHAT_DB/decrypt_copy_MSG0.db', sql,
                            (groupTalkerId, startMsg, groupTalkerId))
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
                    img = decode_dat(wechatFilePath + base64pwd_wxid[1] + '\\' + imgPath)
                except:
                    content = '图片过期或已被清理'
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
