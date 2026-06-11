"""合并旧+新数据源Excel，输出统一格式的合并文件"""
import pandas as pd, os, shutil

OLD = 'D:/工作/workbuddy/外卖业务运营看板数据源5.31-6.2.xlsx'
NEW = 'D:/工作/workbuddy/外卖业务运营看板数据源6.3-6.8.xlsx'
OUT = 'D:/工作/workbuddy/外卖业务运营看板数据源.xlsx'

# 备份旧文件
backup = OLD.replace('.xlsx', '.backup.xlsx')
if not os.path.exists(backup):
    shutil.copy(OLD, backup)
    print(f'已备份旧文件 → {backup}')

# ============================================================
# 1. 架构 (Sheet 名: 美团架构数据源)
#    旧: col[0-10]=品牌,市场,城市,门店编码,门店名称,美团ID,美团账号,美团密码,大区,区域,大店
#    新: col[0-10]=美团ID,美团账号,美团密码,门店编码,门店名称,市场,品牌,城市,大区,区域,大店
#    gen_data.py 期望顺序: 品牌,市场,城市,门店编码,门店名称,美团ID,美团账号,美团密码,大区,区域,大店
# ============================================================
print('\n=== 1. 合并架构 ===')
arch_new = pd.read_excel(NEW, sheet_name='美团架构数据源')
arch_new = arch_new.iloc[:, :11]
# 新文件列顺序: 美团ID,美团账号,美团密码,门店编码,门店名称,市场,品牌,城市,大区,区域,大店
arch_new.columns = ['美团ID','美团账号','美团密码','门店编码','门店名称','市场','品牌','城市','大区','区域','大店']
# 重新排列为 gen_data.py 期望的顺序
arch_merged = arch_new[['品牌','市场','城市','门店编码','门店名称','美团ID','美团账号','美团密码','大区','区域','大店']]
print(f'  架构: {len(arch_merged)} 门店 (使用最新架构)')

# ============================================================
# 2. 美团指标数据源 (旧: Sheet名索引2, 新: Sheet名索引1 — 按名称读取)
# ============================================================
print('\n=== 2. 合并美团指标数据源 ===')
mt_old = pd.read_excel(OLD, sheet_name='美团指标数据源')
mt_new = pd.read_excel(NEW, sheet_name='美团指标数据源')
mt_old_dates = sorted(mt_old['日期'].astype(str).unique())
mt_new_dates = sorted(mt_new['日期'].astype(str).unique())
print(f'  旧日期: {mt_old_dates}')
print(f'  新日期: {mt_new_dates}')

# 相同列结构，直接合并
mt_merged = pd.concat([mt_old, mt_new], ignore_index=True)
mt_merged = mt_merged.drop_duplicates().reset_index(drop=True)
mt_dates = sorted(mt_merged['日期'].astype(str).unique())
print(f'  合并后: {len(mt_merged)} 行, 日期 {mt_dates[0]}~{mt_dates[-1]}')

# ============================================================
# 3. 小程序配送数据源 (旧: Sheet名索引1, 新: Sheet名索引2 — 按名称读取)
# ============================================================
print('\n=== 3. 合并小程序配送数据源 ===')
mini_old = pd.read_excel(OLD, sheet_name='小程序配送数据源')
mini_new = pd.read_excel(NEW, sheet_name='小程序配送数据源')
mini_old_dates = sorted(mini_old['pt(day)'].astype(str).str[:8].unique())
mini_new_dates = sorted(mini_new['pt(day)'].astype(str).str[:8].unique())
print(f'  旧日期: {mini_old_dates}')
print(f'  新日期: {mini_new_dates}')
print(f'  旧行数: {len(mini_old)}, 新行数: {len(mini_new)}')

# 验证列结构
if list(mini_old.columns) != list(mini_new.columns):
    print(f'  WARNING: 列名不同!')
    print(f'  Old only: {set(mini_old.columns) - set(mini_new.columns)}')
    print(f'  New only: {set(mini_new.columns) - set(mini_old.columns)}')
else:
    mini_merged = pd.concat([mini_old, mini_new], ignore_index=True)
    mini_merged = mini_merged.drop_duplicates().reset_index(drop=True)
    print(f'  合并后: {len(mini_merged)} 行')

# ============================================================
# 4. 业绩数据源 (Sheet 名相同，但 市场/品牌 vs 省份 列名不同)
# ============================================================
print('\n=== 4. 合并业绩数据源 ===')
perf_old = pd.read_excel(OLD, sheet_name='业绩数据源')
perf_new = pd.read_excel(NEW, sheet_name='业绩数据源')
perf_old_dates = sorted(perf_old['日期'].astype(str).unique())
perf_new_dates = sorted(perf_new['日期'].astype(str).unique())
print(f'  旧日期: {perf_old_dates}')
print(f'  新日期: {perf_new_dates}')

# 新文件: 省份 列 → 改名为 市场/品牌
if '省份' in perf_new.columns and '市场/品牌' not in perf_new.columns:
    perf_new = perf_new.rename(columns={'省份': '市场/品牌'})
    print(f'  已将新文件 省份 列改名为 市场/品牌')

# 确保列一致
common_cols = list(perf_old.columns)
print(f'  旧列数: {len(perf_old.columns)}, 新列数: {len(perf_new.columns)}')

perf_merged = pd.concat([perf_old, perf_new[common_cols]], ignore_index=True)
perf_merged = perf_merged.drop_duplicates().reset_index(drop=True)
perf_dates = sorted(perf_merged['日期'].astype(str).unique())
print(f'  合并后: {len(perf_merged)} 行, 日期 {perf_dates[0]}~{perf_dates[-1]}')

# ============================================================
# 5. 订单数据源 (结构相同)
# ============================================================
print('\n=== 5. 合并订单数据源 ===')
ord_old = pd.read_excel(OLD, sheet_name='订单数据源')
ord_new = pd.read_excel(NEW, sheet_name='订单数据源')
ord_old_dates = sorted(ord_old['日期'].astype(str).unique())
ord_new_dates = sorted(ord_new['日期'].astype(str).unique())
print(f'  旧日期: {ord_old_dates}')
print(f'  新日期: {ord_new_dates}')

# 新文件列名可能不同
for c in ord_new.columns:
    if c not in ord_old.columns:
        print(f'  WARNING: 新文件多出列: {c}')
for c in ord_old.columns:
    if c not in ord_new.columns:
        print(f'  WARNING: 旧文件多出列: {c}')

ord_merged = pd.concat([ord_old, ord_new], ignore_index=True)
ord_merged = ord_merged.drop_duplicates().reset_index(drop=True)
ord_dates = sorted(ord_merged['日期'].astype(str).unique())
print(f'  合并后: {len(ord_merged)} 行, 日期 {ord_dates[0]}~{ord_dates[-1]}')

# ============================================================
# 写入合并文件 (保持与旧文件相同的 Sheet 顺序)
# ============================================================
print('\n=== 写入合并文件 ===')
with pd.ExcelWriter(OUT, engine='openpyxl') as writer:
    arch_merged.to_excel(writer, sheet_name='美团架构数据源', index=False)
    mini_merged.to_excel(writer, sheet_name='小程序配送数据源', index=False)
    mt_merged.to_excel(writer, sheet_name='美团指标数据源', index=False)
    perf_merged.to_excel(writer, sheet_name='业绩数据源', index=False)
    ord_merged.to_excel(writer, sheet_name='订单数据源', index=False)

print(f'合并文件已保存: {OUT}')
print(f'Sheet 顺序: 架构 → 小程序配送 → 美团指标 → 业绩 → 订单')
print(f'总数据日期范围: 5.31 ~ 6.8')
