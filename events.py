# -*- coding: utf-8 -*-
"""店舗イベントカレンダー。公約＋データ検証に基づく既知イベント日を返す。
strength: 'strong'=データで激熱確認 / 'normal'=公約はあるが効果は中〜要検証。
"""
import calendar
from datetime import date

def events_for(hall, d):
    """d='YYYY-MM-DD' → [(event_name, strength), ...]"""
    y,mo,dd=map(int,d.split("-")); wd=date(y,mo,dd).weekday()
    last=calendar.monthrange(y,mo)[1]
    ev=[]
    # 月末: 過去6回の検証で 駅前+12.5万/アイランド+6.7万/新館+8.7万 と激熱。本館のみ効果薄。
    if dd==last:
        ev.append(("月末",'strong' if hall!="honkan" else 'normal'))
    if hall=="espace_akiba":
        if dd%10==6: ev.append(("6のつく日(ピン王)",'normal'))
        if dd in (1,11,22,25): ev.append(("特定日(ピン王)",'normal'))
    elif hall=="island_akiba":
        if dd==20: ev.append(("20日(ピン王)",'normal'))
    elif hall=="shinkan":
        if dd%10 in (4,7): ev.append(("4/7のつく日",'normal'))
    elif hall=="honkan":
        if dd%10==7: ev.append(("7のつく日",'normal'))
    elif hall=="stardust":
        # 8のつく日: 61日データ検証で 平均総差枚+19.2万(平常+8.7万)/台平均+2361(平常+1282) と激熱確認
        if dd%10==8: ev.append(("8のつく日",'strong'))
    elif hall=="bigdipper":
        # 誕生祭(11/22): 公約かつデータ検証で 22日+21万/11日+19万(全体+15万) と最強
        if dd in (11,22): ev.append(("誕生祭",'strong'))
        # 7のつく日(旧イベ): 残存だが直近データでは効果薄
        if dd%10==7: ev.append(("7のつく日(旧イベ)",'normal'))
    elif hall=="bigapple":
        # 旧イベ(アナスロ/スロマップ記載): 7のつく日・ゾロ目。未検証のためnormal。
        if dd%10==7 or dd in (11,22): ev.append(("旧イベ(7/ゾロ目)",'normal'))
    return ev

def event_label(hall, d):
    ev=events_for(hall,d)
    if not ev: return ""
    return " / ".join(n+("【強】" if s=='strong' else "") for n,s in ev)

def is_event(hall, d, strong_only=False):
    ev=events_for(hall,d)
    if strong_only: return any(s=='strong' for _,s in ev)
    return bool(ev)
