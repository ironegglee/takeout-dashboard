# -*- coding: utf-8 -*-
import openpyxl, json, sys

path = r'D:\工作\杂项\外卖指标.xlsx'
OUT = r'C:\Users\CYYS\WorkBuddy\2026-06-01-16-48-48\filter_options.json'

# === 美团数据源 - 提取市场→城市映射 & 大区→区经理映射 ===
wb1 = openpyxl.load_workbook(path, data_only=True, read_only=True)
ws_mt = wb1['美团数据源']

market_cities = {}  # market -> set of cities
region_areas = {}   # region_mgr -> set of area_mgr

for row in ws_mt.iter_rows(min_row=2, values_only=True):
    if len(row) < 12: continue
    market = str(row[8]).strip() if row[8] else None  # Col9=市场
    city = str(row[6]).strip() if row[6] else None     # Col7=城市
    region = str(row[10]).strip() if row[10] else None  # Col11=大区
    area = str(row[11]).strip() if row[11] else None    # Col12=区域
    
    if market and city:
        market_cities.setdefault(market, set()).add(city)
    if region and area:
        region_areas.setdefault(region, set()).add(area)

wb1.close()

# 转换为sorted
market_cities = {k: sorted(list(v)) for k, v in market_cities.items()}
region_areas = {k: sorted(list(v)) for k, v in region_areas.items()}

result = {
    'market_cities': market_cities,
    'region_areas': region_areas,
}

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print('DONE', file=sys.stderr)
