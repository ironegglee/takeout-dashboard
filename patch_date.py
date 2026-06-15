"""轻量脚本：只读取Excel日期范围，更新data.json的full_date_range字段"""
import pandas as pd, json

DATA_JSON = 'C:/Users/CYYS/WorkBuddy/2026-06-01-16-48-48/dashboard/data.json'
FPATH = 'D:/工作/workbuddy/外卖业务运营看板数据源.xlsx'

# 读取 Sheet1 的日期列
df2 = pd.read_excel(FPATH, sheet_name=1, usecols=[0])  # 只读第一列 pt(day)
df2['日期_dt'] = pd.to_datetime(df2.iloc[:, 0].astype(str), format='%Y%m%d', errors='coerce')
full_min = df2['日期_dt'].min()
full_max = df2['日期_dt'].max()
full_range = f'{full_min.strftime("%Y-%m-%d")} ~ {full_max.strftime("%Y-%m-%d")}'
print(f'全量日期范围: {full_range}')

# 更新 data.json
with open(DATA_JSON, 'r', encoding='utf-8') as f:
    data = json.load(f)
data['full_date_range'] = full_range
with open(DATA_JSON, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False)
print(f'已更新 data.json: full_date_range = {full_range}')
