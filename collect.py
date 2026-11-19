import os
import csv
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))

keys = os.environ.get("BUS_API_KEY").split(",")
url = "http://ws.bus.go.kr/api/rest/buspos/getBusPosByRtid"

# 수집할 노선: [노선번호, 노선ID]
routes = [
    ["040", "104000014"],
    ["641", "100100094"],
    ["650", "100100097"],
    ["753", "100100118"],
    ["5511", "100100250"],
    ["750A", "100100114"],
    ["506", "100100081"],
    ["관악01", "120900005"],
]

windows = [
    ["06:00", "10:30"],
    ["12:00", "14:00"],
    ["16:00", "20:00"],
]


def make_time(hm):
    h, m = hm.split(":")
    return datetime.now(KST).replace(hour=int(h), minute=int(m), second=0, microsecond=0)


def find_window():
    now = datetime.now(KST)
    for w in windows:
        start = make_time(w[0])
        end = make_time(w[1])
        if start - timedelta(minutes=90) <= now < end:
            return start, end
    return None


def collect_once(filename):
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
    file = open(filename, "a", newline="", encoding="utf-8-sig")
    writer = csv.writer(file)

    for i in range(len(routes)):
        no = routes[i][0]
        rid = routes[i][1]
        key = keys[i % len(keys)]

        params = {"serviceKey": key, "busRouteId": rid}
        try:
            response = requests.get(url, params=params, timeout=20)
        except requests.RequestException as e:
            print(no, "번: 요청 실패 →", e)
            continue

        try:
            root = ET.fromstring(response.content)
        except ET.ParseError:
            print(no, "번: 응답 오류 →", response.text[:200])
            continue

        count = 0
        for bus in root.iter("itemList"):
            plain = bus.findtext("plainNo")
            sect = bus.findtext("sectOrd")
            stop = bus.findtext("stopFlag")
            tm = bus.findtext("dataTm")
            writer.writerow([now, no, plain, sect, stop, tm])
            count = count + 1

        print(no, "번:", count, "대 저장")

    file.close()
    print(now, "저장 완료")


window = find_window()

if window is None:
    print("수집 시간대가 아닙니다")
else:
    start, end = window

    if datetime.now(KST) < start:
        wait = (start - datetime.now(KST)).total_seconds()
        print(start.strftime("%H:%M"), "까지", int(wait / 60), "분 대기")
        time.sleep(wait)

    os.makedirs("data", exist_ok=True)
    filename = "data/" + start.strftime("%Y-%m-%d_%H%M") + "_" + datetime.now(KST).strftime("%H%M%S") + ".csv"

    while datetime.now(KST) < end:
        collect_once(filename)
        time.sleep(120)

    print("수집 종료")