"""外卖业务运营看板数据生成脚本 v3
从两个分月数据源按Sheet名读取并内存合并，生成看板JSON。
v3变更：改为双文件直接读取(避免merge_data.py合并大文件慢/易损坏)，按Sheet名称索引。
"""
import pandas as pd, sys, json, re, math
sys.stdout.reconfigure(encoding='utf-8')

OLD_PATH = 'D:/工作/workbuddy/外卖业务运营看板数据源5.31-6.2.backup.xlsx'
NEW_PATH = 'D:/工作/workbuddy/外卖业务运营看板数据源6.3-6.24.xlsx'
OUT = 'C:/Users/CYYS/WorkBuddy/2026-06-16-11-25-31/dashboard/data.json'

BRAND_MAP = {
    '茶颜': '茶颜悦色', '茶颜悦色': '茶颜悦色',
    '鸳央': '鸳央咖啡', '鸳央咖啡': '鸳央咖啡',
    '墨柠': '墨柠', '古德墨柠': '墨柠',
    '昼夜': '昼夜诗', '昼夜诗': '昼夜诗',
    '饼坊': '饼坊'
}

def normalize_brand(val):
    """品牌名统一归一化：处理各种变体/简写/错别字"""
    v = str(val).strip() if pd.notna(val) else ''
    if not v or v == 'nan':
        return ''
    # 精确映射
    if v in BRAND_MAP:
        return BRAND_MAP[v]
    # 模糊匹配
    if '茶颜' in v:
        return '茶颜悦色'
    if '鸳央' in v or '鸯央' in v:
        return '鸳央咖啡'
    if '墨柠' in v or '古德' in v:
        return '墨柠'
    if '昼夜' in v:
        return '昼夜诗'
    if '饼坊' in v or '饼行' in v:
        return '饼坊'
    return v

# 品牌→市场映射：当市场字段被品牌名污染时，根据品牌推断真实市场
BRAND_TO_MARKET = {
    '墨柠': '湖南', '古德墨柠': '湖南',
    '鸳央咖啡': '湖南', '鸳央': '湖南',
    '昼夜诗': '湖南', '昼夜': '湖南',
    '饼坊': '湖南',
}

def normalize_market(market_val, brand_val=''):
    """市场名归一化：去除品牌污染 + 统一省市名格式"""
    v = str(market_val).strip() if pd.notna(market_val) else ''
    if not v or v == 'nan':
        return ''
    
    # 如果市场值本身就是品牌名（或被品牌污染），用品牌→市场映射纠正
    if v in BRAND_TO_MARKET:
        return BRAND_TO_MARKET[v]
    
    # 如果已知品牌且市场值匹配品牌关键词，也纠正
    brand_norm = normalize_brand(brand_val) if brand_val else ''
    if brand_norm in BRAND_TO_MARKET and (brand_norm in v or v in brand_norm or ('墨柠' in v and '墨柠' in brand_norm) or ('鸳央' in v and '鸳央' in brand_norm) or ('昼夜' in v and '昼夜' in brand_norm)):
        return BRAND_TO_MARKET[brand_norm]
    
    # 省市名格式归一化
    MARKET_NORM = {
        '湖南': '湖南', '湖南省': '湖南', '湖南省市场': '湖南',
        '江苏': '江苏', '江苏省': '江苏', '江苏省市场': '江苏',
        '湖北': '湖北', '湖北省': '湖北', '湖北省市场': '湖北',
        '重庆': '重庆', '重庆市': '重庆', '重庆市市场': '重庆',
        '广东': '广东', '广东省': '广东', '广东市场': '广东',
        '深圳': '广东',
    }
    if v in MARKET_NORM:
        return MARKET_NORM[v]
    
    # 模糊匹配：如果市场名包含标准省市名
    for std_name, normed in [('湖南','湖南'),('江苏','江苏'),('湖北','湖北'),('重庆','重庆'),('广东','广东')]:
        if std_name in v and v != normed:
            return normed
    
    return v

def safe_float(val, default=0.0):
    try: v = float(val); return default if math.isnan(v) else v
    except: return default

def safe_int(val, default=0):
    try: return int(float(val))
    except: return default

# ═══════════════════════════════════════════
# 1. 读取架构 (NEW文件「美团架构数据源」, 最新架构)
#    注意: NEW文件列序=美团ID,美团账号,美团密码,门店编码,门店名称,市场,品牌,城市,大区,区域,大店
#    需重排为期望序: 品牌,市场,城市,门店编码,门店名称,美团ID,美团账号,美团密码,大区,区域,大店
# ═══════════════════════════════════════════
print('=== 1. 读取架构 ===')
arch = pd.read_excel(NEW_PATH, sheet_name='美团架构数据源')
# 新版源文件: 美团ID,门店编码,门店名称,市场,品牌,城市,大区,区域,大店 (9列，无账号密码)
# 旧版源文件: 美团ID_raw,美团账号,美团密码,门店编码,门店名称,市场,品牌,城市,大区,区域,大店 (11列)
ncols = arch.shape[1]
if ncols >= 11:
    arch = arch.iloc[:, :11]
    arch.columns = ['美团ID_raw','美团账号','美团密码','门店编码','门店名称','市场','品牌','城市','大区','区域','大店']
    arch = arch[['品牌','市场','城市','门店编码','门店名称','美团ID_raw','美团账号','美团密码','大区','区域','大店']]
    arch.columns = ['品牌','市场','城市','门店编码','门店名称','美团ID','美团账号','美团密码','大区','区域','大店']
else:
    arch.columns = ['美团ID','门店编码','门店名称','市场','品牌','城市','大区','区域','大店']
    arch = arch[['品牌','市场','城市','门店编码','门店名称','美团ID','大区','区域','大店']]
print(f'架构: {len(arch)} 门店')

arch_by_mtid = {}
arch_by_name = {}
arch_by_code = {}

for _, r in arch.iterrows():
    name = str(r['门店名称']) if pd.notna(r['门店名称']) else ''
    # 跳过空名称的架构行（数据源脏数据，5条：Y73100151/C73300018/G73100154/C02300027/C02300028）
    if not name or not name.strip():
        continue
    mtid = str(int(r['美团ID'])) if pd.notna(r['美团ID']) else ''
    city = str(r['城市']) if pd.notna(r['城市']) and str(r['城市']) != 'nan' else ''
    region = str(r['大区']) if pd.notna(r['大区']) else ''
    area = str(r['区域']) if pd.notna(r['区域']) else ''
    leader = str(r['大店']) if pd.notna(r['大店']) else ''
    brand = normalize_brand(r['品牌'])
    market = normalize_market(r['市场'], brand)
    code = str(r['门店编码']) if pd.notna(r['门店编码']) else ''
    
    info = {
        'brand': brand, 'market': market, 'city': city,
        'region_mgr': region, 'area_mgr': area, 'leader': leader,
        'store_code': code, 'arch_name': name
    }
    if mtid:
        arch_by_mtid[mtid] = info
    if name:
        arch_by_name[name] = info
    if code:
        arch_by_code[code] = info

print(f'  有美团ID: {len(arch_by_mtid)}, 有门店名称: {len(arch_by_name)}, 有门店编码: {len(arch_by_code)}')

# ═══════════════════════════════════════════
# 2. 读取美团指标数据 (OLD+NEW「美团指标数据源」内存合并)
#    两文件均有48列含架构字段(门店编码/门店名称.1/市场/品牌/城市/大区/区域/大店)
# ═══════════════════════════════════════════
print('\n=== 2. 读取美团指标数据 ===')
mt_old = pd.read_excel(OLD_PATH, sheet_name='美团指标数据源')
mt_new = pd.read_excel(NEW_PATH, sheet_name='美团指标数据源')
mt = pd.concat([mt_old, mt_new], ignore_index=True).drop_duplicates().reset_index(drop=True)
latest = mt['日期'].max()
# 构建日期列用于过滤
mt['日期_str_raw'] = mt['日期'].apply(lambda x: f'{str(x)[:4]}-{str(x)[4:6]}-{str(x)[6:8]}')
mt['日期_dt'] = pd.to_datetime(mt['日期_str_raw'], format='%Y-%m-%d')
print(f'美团最新日期: {latest}, 总行数: {len(mt)}')
print(f'美团全量日期间: {mt["日期"].min()} ~ {mt["日期"].max()}')

# 构建美团门店维度架构索引: 门店编码 → {brand,market,city,region_mgr,area_mgr,leader,name}
# 用Sheet 2自身的架构列直接匹配，无需再联合Sheet 0
mt_arch = {}
for _, r in mt.iterrows():
    code = str(r.get('门店编码','')) if pd.notna(r.get('门店编码')) else ''
    name_arch = str(r.get('门店名称.1','')) if pd.notna(r.get('门店名称.1')) else ''
    brand = normalize_brand(r.get('品牌'))
    market = normalize_market(r.get('市场'), brand)
    city = str(r.get('城市','')) if pd.notna(r.get('城市')) else ''
    region = str(r.get('大区','')) if pd.notna(r.get('大区')) else ''
    area = str(r.get('区域','')) if pd.notna(r.get('区域')) else ''
    leader = str(r.get('大店','')) if pd.notna(r.get('大店')) else ''
    if code:
        mt_arch[code] = {'brand':brand,'market':market,'city':city,
                         'region_mgr':region,'area_mgr':area,'leader':leader,'arch_name':name_arch}

print(f'美团指标表自带架构: {len(mt_arch)} 门店编码')

# 取最新日期门店
mt_latest = mt[mt['日期'] == latest].copy()
print(f'最新日期美团门店数: {len(mt_latest)}')

# 构建门店明细（仅取"得分"列）
mt_stores = []
mt_unmatched = 0

for _, row in mt_latest.iterrows():
    code = str(row.get('门店编码','')) if pd.notna(row.get('门店编码')) else ''
    
    # 直接用美团指标表自带的架构
    arch_info = mt_arch.get(code)
    if not arch_info:
        # 回退：用Sheet 0架构匹配（门店名称）
        mt_name = str(row['门店名称'])
        mt_id = str(row['门店id']).replace('.0','').strip()
        # 尝试匹配
        found = arch_by_mtid.get(mt_id) or arch_by_name.get(mt_name)
        if found:
            arch_info = found
        else:
            # 模糊匹配
            for an, ai in arch_by_name.items():
                if an in mt_name or mt_name in an:
                    arch_info = ai; break
        if not arch_info:
            mt_unmatched += 1
            continue

    shop_score = safe_float(row.get('店铺分'))
    exp_score = safe_float(row.get('综合体验分'))

    mt_stores.append({
        'code': code,
        'name': arch_info['arch_name'],
        'brand': arch_info['brand'], 'market': arch_info['market'],
        'city': arch_info['city'],
        'region_mgr': arch_info['region_mgr'], 'area_mgr': arch_info['area_mgr'],
        'leader': arch_info['leader'], 'channel': 'mt',
        'shop_score': shop_score, 'exp_score': exp_score,
        # shop_dims: 店铺分下属指标 — 只取"得分"列
        'shop_dims': {
            'peak_hours': safe_float(row.get('高峰营业时长得分')),         # 得分
            'quality_rate': safe_float(row.get('优质商品率得分')),         # 得分
            'reject_rate': safe_float(row.get('商家不接单率得分')),        # 得分
            'reply_rate': safe_float(row.get('差评回复率得分')),           # 得分
            'merchant_rating': safe_float(row.get('商家评分得分')),        # 得分
            'menu_rich': safe_float(row.get('菜单丰富度得分')),             # 得分
            'decor_rich': safe_float(row.get('装修丰富度得分')),            # 得分
            'service_rich': safe_float(row.get('服务功能丰富度得分')),      # 得分
            'cook_report': safe_float(row.get('出餐完成上报率得分/配送准时率得分')),  # 得分
            'base_hours': safe_float(row.get('基础营业时长得分')),         # 得分
        },
        # exp_dims: 综合体验分下属指标 — 只取"得分"/"分"列
        'exp_dims': {
            'product_quality': safe_float(row.get('商品质量分')),
            'service_exp': safe_float(row.get('服务体验分')),
            'product_sat': safe_float(row.get('商品满意度')),
            'pack_sat': safe_float(row.get('包装满意度')),
            'repurchase': safe_float(row.get('复购率指标得分')),           # 得分
            'msg_reply': safe_float(row.get('消息回复率指标得分')),        # 得分
            'service_neg': safe_float(row.get('服务负反馈率指标得分')),    # 得分
            'food_safety': safe_float(row.get('食品安全负反馈率指标得分')), # 得分（v2改为得分列）
            'cook_report': safe_float(row.get('出餐完成上报率得分/配送准时率得分')),  # 得分
        }
    })

mt_stores = [s for s in mt_stores if s.get('name') and s.get('brand') and s['brand'] != 'nan']
print(f'美团门店匹配: {len(mt_stores)}/{len(mt_latest)}, 未匹配: {mt_unmatched}')

# ═══════════════════════════════════════════
# 3. 小程序配送数据 (NEW文件「小程序配送数据源」)
# ═══════════════════════════════════════════
print('\n=== 3. 小程序配送数据 ===')
df2 = pd.read_excel(NEW_PATH, sheet_name='小程序配送数据源')
df2['日期_dt'] = pd.to_datetime(df2['pt(day)'].astype(str), format='%Y%m%d', errors='coerce')
max_date = df2['日期_dt'].max()
df2_7d = df2[df2['日期_dt'] >= max_date - pd.Timedelta(days=6)].copy()
print(f'小程序总订单: {len(df2)} 行, 7日: {len(df2_7d)} 行')

def parse_min(v):
    try: return float(v)
    except: return None

df2_7d['制作分钟'] = df2_7d['制作时长'].apply(parse_min)
df2_7d['达标'] = df2_7d['制作分钟'].apply(lambda x: 1 if x is not None and x <= 15 else 0)

# 按门店聚合
agg = df2_7d.groupby(['门店名称', '门店代码', '城市']).agg(
    总订单=('订单数', 'count'),
    总杯数=('订单杯数', 'sum'),
    出餐均值=('制作分钟', 'mean'),
    达标数=('达标', 'sum'),
).reset_index()
agg['出餐达标率'] = (agg['达标数'] / agg['总订单'] * 100).round(1)
agg['出餐均值'] = agg['出餐均值'].round(1)

# 出餐耗时时段分布
df2_7d['cook_hour'] = pd.to_numeric(df2_7d.iloc[:, 26], errors='coerce')
df2_7d['cook_time_val'] = pd.to_numeric(df2_7d.iloc[:, 21], errors='coerce')
df2_valid = df2_7d.dropna(subset=['cook_hour', 'cook_time_val'])
df2_valid = df2_valid[(df2_valid['cook_hour'] >= 7) & (df2_valid['cook_hour'] <= 24)]

hourly_avg = df2_valid.groupby('cook_hour')['cook_time_val'].mean().round(1)
mp_hourly_cook = {}
for h in range(7, 25):
    v = hourly_avg.get(float(h))
    mp_hourly_cook[str(h)] = round(float(v), 1) if v is not None and not (isinstance(v, float) and math.isnan(v)) else 0.0

# 出餐分段占比
total_valid = len(df2_valid)
bins = [(0,5),(5,10),(10,15),(15,20),(20,999)]
labels = ['0-5分钟','5-10分钟','10-15分钟','15-20分钟','20分钟以上']
colors_bd = ['#3B6D11','#639922','#EF9F27','#E24B4A','#A32D2D']
mp_breakdown = []
for (lo,hi),label,color in zip(bins,labels,colors_bd):
    cnt = len(df2_valid[(df2_valid['cook_time_val']>=lo)&(df2_valid['cook_time_val']<hi)])
    pct = round(cnt/total_valid*100,1) if total_valid>0 else 0
    mp_breakdown.append({'label':label,'pct':pct,'color':color,'count':int(cnt)})

# MP门店明细
mp_stores = []
mp_unmatched = []

for _, row in agg.iterrows():
    mp_name = str(row['门店名称'])
    # 跳过空名称门店（数据源脏数据，会导致模糊匹配误命中）
    if not mp_name or not mp_name.strip():
        continue
    code = str(row['门店代码']) if pd.notna(row['门店代码']) else ''
    
    # 优先用门店代码匹配架构
    info = arch_by_code.get(code) or arch_by_name.get(mp_name)
    
    if not info:
        for an, ai in arch_by_name.items():
            if (an and mp_name) and (an in mp_name or mp_name in an):
                info = ai; break
    
    if not info:
        mp_unmatched.append(mp_name)
        continue
    
    avg_cook = safe_float(row['出餐均值'])
    rate = safe_float(row['出餐达标率'])
    
    mp_stores.append({
        'code': code,
        'name': info['arch_name'],
        'brand': info['brand'], 'market': info['market'],
        'city': info['city'],
        'region_mgr': info['region_mgr'], 'area_mgr': info['area_mgr'],
        'leader': info['leader'], 'channel': 'mp',
        'avg': round(avg_cook, 1),
        'rate': round(rate, 1),
        'orders': safe_int(row['总订单']),
        'cups': safe_int(row['总杯数']),
    })

mp_stores = [s for s in mp_stores if s.get('name') and s.get('brand') and s['brand'] != 'nan']
print(f'小程序匹配: {len(mp_stores)}/{len(agg)}, 未匹配: {len(mp_unmatched)}')

# ═══════════════════════════════════════════
# 4. 业绩数据源 (OLD+NEW「业绩数据源」内存合并)
#    注意: OLD文件col[24]=市场/品牌, NEW文件col[24]=省份, 需统一列名后合并
# ═══════════════════════════════════════════
print('\n=== 4. 业绩数据源 ===')
perf_old = pd.read_excel(OLD_PATH, sheet_name='业绩数据源')
try:
    perf_new = pd.read_excel(NEW_PATH, sheet_name='业绩数据源')
except ValueError:
    print('  ⚠ NEW文件无「业绩数据源」sheet，仅使用OLD数据')
    perf_new = pd.DataFrame(columns=perf_old.columns)
# 统一列名: NEW的「省份」→「市场/品牌」(与OLD对齐)
if '省份' in perf_new.columns and '市场/品牌' not in perf_new.columns:
    perf_new = perf_new.rename(columns={'省份': '市场/品牌'})
perf = pd.concat([perf_old, perf_new], ignore_index=True).drop_duplicates().reset_index(drop=True)
perf['日期_dt'] = pd.to_datetime(perf['日期'].astype(str), format='%Y%m%d', errors='coerce')
perf['品牌'] = perf['品牌'].apply(normalize_brand)
perf['region_mgr'] = perf['大区'].astype(str)
perf['area_mgr'] = perf['区经理'].astype(str)
perf['leader'] = perf['大店长'].astype(str)
perf['city'] = perf['城市'].astype(str)
perf['外卖总_val'] = pd.to_numeric(perf['外卖总业绩'], errors='coerce').fillna(0)
perf['小程序外卖_val'] = pd.to_numeric(perf['小程序外卖订单总金额'], errors='coerce').fillna(0)
perf['美团_val'] = pd.to_numeric(perf['美团订单总金额'], errors='coerce').fillna(0)
perf['大盘_val'] = pd.to_numeric(perf['订单总金额'], errors='coerce').fillna(0)  # 全渠道总业绩(含堂食)

# 将业绩数据源中不在架构表的门店编码补入 arch_by_code（解决 store_daily.total 中约363家堂食门店无组织信息的问题）
_perf_codes = perf[['门店编码','门店名称','品牌','市场/品牌','城市','大区','区经理','大店长']].drop_duplicates()
_extended = 0
for _, r in _perf_codes.iterrows():
    code = str(r['门店编码']) if pd.notna(r['门店编码']) else ''
    if not code or code in arch_by_code:
        continue
    name = str(r['门店名称']) if pd.notna(r['门店名称']) else ''
    brand = normalize_brand(r['品牌'])
    market = normalize_market(r['市场/品牌'], brand)
    city = str(r['城市']) if pd.notna(r['城市']) and str(r['城市']) != 'nan' else ''
    region = str(r['大区']) if pd.notna(r['大区']) else ''
    area = str(r['区经理']) if pd.notna(r['区经理']) else ''
    leader = str(r['大店长']) if pd.notna(r['大店长']) else ''
    arch_by_code[code] = {
        'brand': brand, 'market': market, 'city': city,
        'region_mgr': region, 'area_mgr': area, 'leader': leader,
        'store_code': code, 'arch_name': name
    }
    _extended += 1
print(f'  arch_by_code 补全: +{_extended} (总计{len(arch_by_code)})')

# 业绩每日汇总（分渠道）
perf_daily = perf.groupby('日期_dt').agg(
    revenue=('外卖总_val', 'sum'),
    mp_revenue=('小程序外卖_val', 'sum'),
    mt_revenue=('美团_val', 'sum'),
    total_revenue=('大盘_val', 'sum'),  # 大盘业绩（全渠道含堂食）
    store_count=('门店编码', 'nunique'),
    mp_stores=('门店编码', lambda x: x[perf.loc[x.index,'小程序外卖_val']>0].nunique()),
    mt_stores=('门店编码', lambda x: x[perf.loc[x.index,'美团_val']>0].nunique()),
    total_stores=('门店编码', lambda x: x[perf.loc[x.index,'大盘_val']>0].nunique()),
).reset_index()
perf_daily['date'] = perf_daily['日期_dt'].dt.strftime('%Y-%m-%d')
perf_daily['revenue'] = perf_daily['revenue'].round(0).astype(int)
perf_daily['mp_revenue'] = perf_daily['mp_revenue'].round(0).astype(int)
perf_daily['mt_revenue'] = perf_daily['mt_revenue'].round(0).astype(int)
perf_daily['total_revenue'] = perf_daily['total_revenue'].round(0).astype(int)
perf_daily['mp_stores'] = perf_daily['mp_stores'].astype(int)
perf_daily['mt_stores'] = perf_daily['mt_stores'].astype(int)
perf_daily['total_stores'] = perf_daily['total_stores'].astype(int)
print(f'业绩每日: {len(perf_daily)} 天, 大盘 {perf_daily["total_revenue"].sum():.0f}, 外卖总 {perf_daily["revenue"].sum():.0f}, 小程序 {perf_daily["mp_revenue"].sum():.0f}, 美团 {perf_daily["mt_revenue"].sum():.0f}')

# 业绩门店维度汇总（最新7天，分渠道）
perf_max = perf['日期_dt'].max()
perf_7d = perf[perf['日期_dt'] >= perf_max - pd.Timedelta(days=6)]
perf_store = perf_7d.groupby(['门店编码','门店名称','品牌','市场/品牌','city','region_mgr','area_mgr','leader']).agg(
    revenue=('外卖总_val', 'sum'),
    mp_revenue=('小程序外卖_val', 'sum'),
    mt_revenue=('美团_val', 'sum'),
    days=('日期', 'nunique'),
).reset_index()
perf_store['revenue'] = perf_store['revenue'].round(0).astype(int)
perf_store['mp_revenue'] = perf_store['mp_revenue'].round(0).astype(int)
perf_store['mt_revenue'] = perf_store['mt_revenue'].round(0).astype(int)

# 构建门店编码→业绩映射（分渠道）
perf_by_code = {}
for _, r in perf_store.iterrows():
    code = str(r['门店编码']) if pd.notna(r['门店编码']) else ''
    if code:
        perf_by_code[code] = {
            'revenue': int(r['revenue']), 'mp_revenue': int(r['mp_revenue']),
            'mt_revenue': int(r['mt_revenue']), 'days': int(r['days']),
            'market': normalize_market(r['市场/品牌'], r['品牌'])
        }

print(f'业绩门店数(7日): {len(perf_by_code)}')

# ═══════════════════════════════════════════
# 5. 订单数据源 (OLD+NEW「订单数据源」内存合并)
# ═══════════════════════════════════════════
print('\n=== 5. 订单数据源 ===')
orders_old = pd.read_excel(OLD_PATH, sheet_name='订单数据源')
try:
    orders_new = pd.read_excel(NEW_PATH, sheet_name='订单数据源')
except ValueError:
    print('  ⚠ NEW文件无「订单数据源」sheet，仅使用OLD数据')
    orders_new = pd.DataFrame(columns=orders_old.columns)
orders_df = pd.concat([orders_old, orders_new], ignore_index=True).drop_duplicates().reset_index(drop=True)
orders_df['日期_dt'] = pd.to_datetime(orders_df['日期'].astype(str), format='%Y%m%d', errors='coerce')
orders_df['品牌'] = orders_df['品牌'].apply(normalize_brand)
orders_df['region_mgr'] = orders_df['大区'].astype(str)
orders_df['area_mgr'] = orders_df['区经理'].astype(str)
orders_df['leader'] = orders_df['大店长'].astype(str)
orders_df['外卖总_val'] = pd.to_numeric(orders_df['外卖总'], errors='coerce').fillna(0).astype(int)
orders_df['有效订单数_val'] = pd.to_numeric(orders_df['有效订单数'], errors='coerce').fillna(0).astype(int)
orders_df['小程序外卖_val'] = pd.to_numeric(orders_df['小程序外卖订单数'], errors='coerce').fillna(0).astype(int)
orders_df['美团_val'] = pd.to_numeric(orders_df['美团订单数'], errors='coerce').fillna(0).astype(int)

# 订单每日汇总（分渠道）
# 外卖门店数=业绩数据源外卖总非0；小程序/美团门店数=订单数据源对应字段非0
order_daily = orders_df.groupby('日期_dt').agg(
    orders=('外卖总_val', 'sum'),
    total_orders=('有效订单数_val', 'sum'),  # 大盘订单（全渠道）
    mp_orders=('小程序外卖_val', 'sum'),
    mt_orders=('美团_val', 'sum'),
    store_count=('门店编码', 'nunique'),
    mp_stores=('门店编码', lambda x: x[orders_df.loc[x.index,'小程序外卖_val']>0].nunique()),
    mt_stores=('门店编码', lambda x: x[orders_df.loc[x.index,'美团_val']>0].nunique()),
    total_stores=('门店编码', lambda x: x[orders_df.loc[x.index,'有效订单数_val']>0].nunique()),
).reset_index()
order_daily['date'] = order_daily['日期_dt'].dt.strftime('%Y-%m-%d')
order_daily['orders'] = order_daily['orders'].astype(int)
order_daily['mp_orders'] = order_daily['mp_orders'].astype(int)
order_daily['mt_orders'] = order_daily['mt_orders'].astype(int)
order_daily['mp_stores'] = order_daily['mp_stores'].astype(int)
order_daily['mt_stores'] = order_daily['mt_stores'].astype(int)
print(f'订单每日: {len(order_daily)} 天, 外卖总 {order_daily["orders"].sum():.0f}, 小程序 {order_daily["mp_orders"].sum():.0f}, 美团 {order_daily["mt_orders"].sum():.0f}')

# 订单门店维度汇总（最新7天，分渠道）
order_max = orders_df['日期_dt'].max()
order_7d = orders_df[orders_df['日期_dt'] >= order_max - pd.Timedelta(days=6)].copy()
order_7d['city'] = order_7d['城市'].astype(str)
order_store = order_7d.groupby(['门店编码','门店名称','品牌','city','region_mgr','area_mgr','leader']).agg(
    orders=('外卖总_val', 'sum'),
    total_orders=('有效订单数_val', 'sum'),
    mp_orders=('小程序外卖_val', 'sum'),
    mt_orders=('美团_val', 'sum'),
    days=('日期', 'nunique'),
).reset_index()
order_store['orders'] = order_store['orders'].astype(int)
order_store['total_orders'] = order_store['total_orders'].astype(int)
order_store['mp_orders'] = order_store['mp_orders'].astype(int)
order_store['mt_orders'] = order_store['mt_orders'].astype(int)

order_by_code = {}
for _, r in order_store.iterrows():
    code = str(r['门店编码']) if pd.notna(r['门店编码']) else ''
    if code:
        order_by_code[code] = {
            'orders': int(r['orders']), 'total_orders': int(r['total_orders']),
            'mp_orders': int(r['mp_orders']), 'mt_orders': int(r['mt_orders']), 'days': int(r['days'])
        }

print(f'订单门店数(7日): {len(order_by_code)}')

# ═══════════════════════════════════════════
# 6. 合并业绩/订单到门店数据（分渠道）
# ═══════════════════════════════════════════
print('\n=== 6. 合并业绩/订单 ===')

# 门店编码→架构映射(反向)
arch_name_to_code = {}
for code, info in arch_by_code.items():
    arch_name_to_code[info['arch_name']] = code

def attach_perf_order(stores_list, channel):
    """给门店列表附加业绩和订单数据，按渠道区分"""
    for s in stores_list:
        code = arch_name_to_code.get(s['name'], '')
        if code:
            p = perf_by_code.get(code, {})
            o = order_by_code.get(code, {})
            if channel == 'mp':
                s['revenue'] = p.get('mp_revenue', 0)
                s['orders'] = o.get('mp_orders', 0)
            elif channel == 'mt':
                s['revenue'] = p.get('mt_revenue', 0)
                s['orders'] = o.get('mt_orders', 0)
            else:
                s['revenue'] = p.get('revenue', 0)
                s['orders'] = o.get('orders', 0)
        else:
            s['revenue'] = 0
            s['orders'] = 0
    return stores_list

mp_stores = attach_perf_order(mp_stores, 'mp')
mt_stores = attach_perf_order(mt_stores, 'mt')

# ═══════════════════════════════════════════
# 6b. 大盘业绩汇总（全渠道，独立于小程序/美团模块）
# ═══════════════════════════════════════════
print('\n=== 6b. 大盘业绩汇总 ===')
perf_7d_total = perf_store['revenue'].sum()
perf_7d_mp = perf_store['mp_revenue'].sum()
perf_7d_mt = perf_store['mt_revenue'].sum()
# 近7天有业绩的门店数（分渠道）
perf_7d_stores_total = len(perf_store)
perf_7d_stores_mp = int((perf_store['mp_revenue'] > 0).sum())
perf_7d_stores_mt = int((perf_store['mt_revenue'] > 0).sum())
perf_days = int(perf_7d['日期'].nunique()) if len(perf_7d) > 0 else 7

order_7d_total = order_store['orders'].sum()
order_7d_total_all = order_store['total_orders'].sum()  # 大盘订单（全渠道有效订单数）
order_7d_mp = order_store['mp_orders'].sum()
order_7d_mt = order_store['mt_orders'].sum()
order_7d_stores_total = len(order_store)
order_7d_stores_mp = int((order_store['mp_orders'] > 0).sum())
order_7d_stores_mt = int((order_store['mt_orders'] > 0).sum())

def calc_daily_avg(total, stores, days):
    """店日均 = 总额 ÷ 门店数 ÷ 天数"""
    if stores > 0 and days > 0:
        return round(total / stores / days, 1)
    return 0

dashboard_summary = {
    'days': perf_days,
    'revenue': {
        'total': int(perf_7d_total),
        'mp': int(perf_7d_mp),
        'mt': int(perf_7d_mt),
        'mt_pct': round(perf_7d_mt / perf_7d_total * 100, 1) if perf_7d_total > 0 else 0,
    },
    'tc': {
        'total': int(order_7d_total),
        'total_all': int(order_7d_total_all),  # 大盘订单（全渠道有效订单数）
        'mp': int(order_7d_mp),
        'mt': int(order_7d_mt),
        'mt_pct': round(order_7d_mt / order_7d_total * 100, 1) if order_7d_total > 0 else 0,
    },
    'stores': {
        'total': perf_7d_stores_total,
        'mp': perf_7d_stores_mp,
        'mt': perf_7d_stores_mt,
        'mt_pct': round(perf_7d_stores_mt / perf_7d_stores_total * 100, 1) if perf_7d_stores_total > 0 else 0,
    },
    'daily_avg_revenue': {
        'total': calc_daily_avg(perf_7d_total, perf_7d_stores_total, perf_days),
        'mp': calc_daily_avg(perf_7d_mp, perf_7d_stores_mp, perf_days),
        'mt': calc_daily_avg(perf_7d_mt, perf_7d_stores_mt, perf_days),
    },
    'daily_avg_tc': {
        'total': round(order_7d_total / perf_7d_stores_total / perf_days, 1) if perf_7d_stores_total > 0 else 0,
        'mp': round(order_7d_mp / perf_7d_stores_mp / perf_days, 1) if perf_7d_stores_mp > 0 else 0,
        'mt': round(order_7d_mt / perf_7d_stores_mt / perf_days, 1) if perf_7d_stores_mt > 0 else 0,
    },
}

print(f'大盘汇总: 业绩总{perf_7d_total/10000:.1f}万(小程序{perf_7d_mp/10000:.1f}万/美团{perf_7d_mt/10000:.1f}万), '
      f'TC总{order_7d_total}(小程序{order_7d_mp}/美团{order_7d_mt}), '
      f'门店总{perf_7d_stores_total}(小程序{perf_7d_stores_mp}/美团{perf_7d_stores_mt}), '
      f'天数{perf_days}')

# ═══════════════════════════════════════════
# 7. 预警中心数据
# ═══════════════════════════════════════════
print('\n=== 7. 预警中心 ===')

alerts = []

# ① 当前北京时间（今天）近7天连续2天出餐时间超过15分钟
from datetime import datetime as dt_mod
today = dt_mod.now()
ref_date = pd.Timestamp(today.strftime('%Y-%m-%d'))
cutoff = ref_date - pd.Timedelta(days=7)

print(f'  检测: 出餐超时预警（参考日期={ref_date.date()}，窗口={cutoff.date()}~{ref_date.date()}）...')
df2['cook_min_full'] = pd.to_numeric(df2['制作时长'], errors='coerce')
df2['日期_str'] = df2['日期_dt'].dt.strftime('%Y-%m-%d')
df2_recent = df2[(df2['日期_dt'] >= cutoff) & (df2['日期_dt'] <= ref_date)]

# 按店+日计算日均出餐，找出连续2天>15的
daily_cook = df2_recent.groupby(['门店名称','日期_str'])['cook_min_full'].mean().reset_index()
daily_cook['over15'] = daily_cook['cook_min_full'] > 15
daily_cook = daily_cook.sort_values(['门店名称','日期_str'])

over15_stores = {}
for name in daily_cook['门店名称'].unique():
    store_data = daily_cook[daily_cook['门店名称'] == name].reset_index(drop=True)
    bad_dates_all = store_data[store_data['over15']]['日期_str'].tolist()
    for i in range(len(store_data)-1):
        if store_data.loc[i,'over15'] and store_data.loc[i+1,'over15']:
            bad_days_data = store_data[store_data['over15']]
            over15_stores[str(name)] = {
                'dates': bad_dates_all,
                'avg': round(store_data['cook_min_full'].mean(), 1),
                'max': round(store_data['cook_min_full'].max(), 1),
                'bad_avg': round(bad_days_data['cook_min_full'].mean(), 1) if len(bad_days_data) > 0 else 0,
            }
            break

for mp_name, cook_info in over15_stores.items():
    info = arch_by_name.get(mp_name)
    if not info:
        for an, ai in arch_by_name.items():
            if an in mp_name or mp_name in an:
                info = ai; break
    if info:
        bad_dates = cook_info['dates']
        alerts.append({
            'type': 'cook',
            'store': info['arch_name'],
            'brand': info['brand'],
            'market': info['market'],
            'city': info['city'],
            'region_mgr': info['region_mgr'],
            'area_mgr': info['area_mgr'],
            'leader': info['leader'],
            'msg': f'连续2天出餐超15分钟（{bad_dates[0]}~{bad_dates[-1]}），峰值 {cook_info["max"]} 分钟',
            'detail': f'峰值出餐 {cook_info["max"]} 分钟 | 日均 {cook_info["avg"]} 分钟 | 超时日期: {",".join(bad_dates)}',
            'max_cook': cook_info['max'],
            'avg_cook': cook_info['avg'],
        })

print(f'  出餐超时预警: {len(alerts)} 条')

# ② 店铺分：任一维度低于80分（mt_stores 已从最新日期构建，无需再过滤）
# 注意：得分=0 也应被标记（如新店数据缺失导致某维度为0分），不能隐藏
print('  检测: 店铺分预警...')

dim_labels = {
    'peak_hours': '高峰营业时长得分', 'quality_rate': '优质商品率得分',
    'reject_rate': '商家不接单率得分', 'reply_rate': '差评回复率得分',
    'merchant_rating': '商家评分得分', 'menu_rich': '菜单丰富度得分',
    'decor_rich': '装修丰富度得分', 'service_rich': '服务功能丰富度得分',
    'cook_report': '出餐上报/配送准时率得分', 'base_hours': '基础营业时长得分'
}

for s in mt_stores:
    low_dims = []
    all_dim_strs = []
    for dim_name in ['peak_hours','quality_rate','reject_rate','reply_rate','merchant_rating',
                      'menu_rich','decor_rich','service_rich','cook_report','base_hours']:
        dim_val = s.get('shop_dims', {}).get(dim_name, 0)
        label = dim_labels.get(dim_name, dim_name)
        # 0分也必须展示，不隐藏
        if dim_val < 80:
            suffix = ' ⚠' if dim_val < 80 else ''
            dim_str = f'{label}{dim_val}分{suffix}'
            low_dims.append({'name': label, 'val': dim_val})
            all_dim_strs.append(dim_str)
        else:
            all_dim_strs.append(f'{label}{dim_val}分')
    if low_dims:
        msg = f'{len(low_dims)}项低于80分'
        alerts.append({
            'type': 'shop',
            'store': s['name'], 'brand': s['brand'], 'market': s['market'],
            'city': s['city'], 'region_mgr': s['region_mgr'],
            'area_mgr': s['area_mgr'], 'leader': s['leader'],
            'msg': msg,
            'detail': '; '.join([f"{d['name']}{d['val']}分" for d in low_dims]),
            'shop_score': s.get('shop_score', 0),
            'low_dims': low_dims,
        })

print(f'  店铺分预警: {sum(1 for a in alerts if a["type"]=="shop")} 条')

# ③ 综合体验分预警：低于4.6分，需展示各子维度明细
print('  检测: 综合体验分预警...')
exp_dim_labels = {
    'product_quality': '商品质量分', 'service_exp': '服务体验分',
    'product_sat': '商品满意度', 'pack_sat': '包装满意度',
    'repurchase': '复购率指标', 'msg_reply': '消息回复率',
    'service_neg': '服务负反馈率', 'food_safety': '食品安全负反馈率',
    'cook_report': '出餐上报/配送准时率',
}
for s in mt_stores:
    exp_score = s.get('exp_score', 0)
    if exp_score < 4.6:
        # 分析各体验分维度，找出问题维度
        exp_dims_raw = s.get('exp_dims', {})
        low_exp_dims = []
        all_exp_dim_strs = []
        for dim_key in ['product_quality','service_exp','product_sat','pack_sat',
                         'repurchase','msg_reply','service_neg','food_safety','cook_report']:
            dim_val = exp_dims_raw.get(dim_key, 0)
            label = exp_dim_labels.get(dim_key, dim_key)
            all_exp_dim_strs.append(f'{label}{dim_val:.1f}分')
            # 体验分子维度通常满分5分，低于4.2算问题维度
            if dim_val > 0 and dim_val < 4.2:
                low_exp_dims.append({'name': label, 'val': round(dim_val, 1)})
        
        # 构建详情：优先展示问题维度，附带完整维度列表
        if low_exp_dims:
            problem_str = '; '.join([f"{d['name']}{d['val']}分" for d in low_exp_dims])
            detail = f'综合体验分 {exp_score:.2f} 分 | 问题维度: {problem_str} | 全维度: {"; ".join(all_exp_dim_strs)}'
        else:
            detail = f'综合体验分 {exp_score:.2f} 分 | 全维度: {"; ".join(all_exp_dim_strs)}'
        
        alerts.append({
            'type': 'rating',
            'store': s['name'], 'brand': s['brand'], 'market': s['market'],
            'city': s['city'], 'region_mgr': s['region_mgr'],
            'area_mgr': s['area_mgr'], 'leader': s['leader'],
            'msg': f'综合体验分 {exp_score:.2f} 分（低于4.6分）',
            'detail': detail,
            'exp_score': round(exp_score, 2),
            'exp_dims': exp_dims_raw,
            'low_dims': low_exp_dims,
        })

print(f'  综合体验分预警: {sum(1 for a in alerts if a["type"]=="rating")} 条')
print(f'  预警总数: {len(alerts)} 条')

# ═══════════════════════════════════════════
# 8. 每日汇总（供前端日期过滤）
# ═══════════════════════════════════════════
print('\n=== 8. 每日汇总 ===')

# 小程序每日
df2['cook_min'] = pd.to_numeric(df2['制作时长'], errors='coerce')
df2['comply'] = (df2['cook_min'] <= 15).astype(int)
daily_mp = df2.groupby('日期_dt').agg(
    orders=('订单数', 'count'),
    avg_cook=('cook_min', 'mean'),
    comply_cnt=('comply', 'sum'),
    store_count=('门店代码', 'nunique'),
).reset_index()
daily_mp['avg_cook'] = daily_mp['avg_cook'].round(1)
daily_mp['rate'] = (daily_mp['comply_cnt'] / daily_mp['orders'] * 100).round(1)
daily_mp['date'] = daily_mp['日期_dt'].dt.strftime('%Y-%m-%d')
mp_daily = daily_mp[['date','orders','avg_cook','rate','store_count']].to_dict('records')
for r in mp_daily:
    r['orders'] = int(r['orders'])
    r['store_count'] = int(r['store_count'])
print(f'mp_daily: {len(mp_daily)} 天')

# 美团每日（评分+架构匹配的营收）
mt['日期_str'] = mt['日期'].apply(lambda x: f'{str(x)[:4]}-{str(x)[4:6]}-{str(x)[6:8]}')
mt['店铺分_v'] = pd.to_numeric(mt['店铺分'], errors='coerce').fillna(0)
mt['体验分_v'] = pd.to_numeric(mt['综合体验分'], errors='coerce').fillna(0)
daily_mt = mt.groupby('日期_str').agg(
    avg_shop=('店铺分_v', 'mean'),
    avg_exp=('体验分_v', 'mean'),
    stores=('门店名称', 'nunique'),
).reset_index()
daily_mt['avg_shop'] = daily_mt['avg_shop'].round(1)
daily_mt['avg_exp'] = daily_mt['avg_exp'].round(2)
mt_daily = daily_mt.rename(columns={'日期_str':'date','avg_shop':'avg_shop_score','avg_exp':'avg_exp_score','stores':'store_count'}).to_dict('records')
for r in mt_daily:
    r['store_count'] = int(r['store_count'])
print(f'mt_daily: {len(mt_daily)} 天')

# 业绩每日
perf_daily_list = perf_daily[['date','revenue','mp_revenue','mt_revenue','total_revenue','store_count','mp_stores','mt_stores']].to_dict('records')
for r in perf_daily_list:
    r['store_count'] = int(r['store_count'])
    r['mp_stores'] = int(r.get('mp_stores', 0))
    r['mt_stores'] = int(r.get('mt_stores', 0))
print(f'perf_daily: {len(perf_daily_list)} 天')

# 全量日期范围（业绩数据覆盖5.1~最新）
full_date_range = ''
if perf_daily_list:
    dates = sorted(r['date'] for r in perf_daily_list)
    full_date_range = f'{dates[0]} ~ {dates[-1]}'
    print(f'full_date_range: {full_date_range}')

# 订单每日
order_daily_list = order_daily[['date','orders','total_orders','mp_orders','mt_orders','store_count','mp_stores','mt_stores','total_stores']].to_dict('records')
for r in order_daily_list:
    r['store_count'] = int(r['store_count'])
    r['mp_stores'] = int(r.get('mp_stores', 0))
    r['mt_stores'] = int(r.get('mt_stores', 0))
    r['total_stores'] = int(r.get('total_stores', 0))
print(f'order_daily: {len(order_daily_list)} 天')

# 日期范围
mp_date_range = ''
if '日期_dt' in df2.columns and not df2['日期_dt'].empty:
    dmin = df2['日期_dt'].min().strftime('%Y-%m-%d')
    dmax = df2['日期_dt'].max().strftime('%Y-%m-%d')
    mp_date_range = f'{dmin} ~ {dmax}'

# ═══════════════════════════════════════════
# 8b. 每日门店列表（供前端日期筛选时门店去重）
# ═══════════════════════════════════════════
print('\n=== 8b. 每日门店列表（去重用）===')
perf['日期_str'] = perf['日期_dt'].dt.strftime('%Y-%m-%d')
store_daily = {}
for date_str, grp in perf.groupby('日期_str'):
    codes_mp = grp[grp['小程序外卖_val'] > 0]['门店编码'].astype(str).unique().tolist()
    codes_mt = grp[grp['美团_val'] > 0]['门店编码'].astype(str).unique().tolist()
    codes_all = grp[grp['外卖总_val'] > 0]['门店编码'].astype(str).unique().tolist()
    codes_total = grp[grp['大盘_val'] > 0]['门店编码'].astype(str).unique().tolist()  # 订单总金额>0=堂食营业
    store_daily[str(date_str)] = {
        'mp': codes_mp,
        'mt': codes_mt,
        'all': codes_all,
        'total': codes_total
    }
print(f'store_daily: {len(store_daily)} 天')

# TC-based store daily (from 订单数据源: 有效订单数>0)
orders_df['日期_str'] = orders_df['日期_dt'].dt.strftime('%Y-%m-%d')
for date_str, grp in orders_df.groupby('日期_str'):
    if date_str not in store_daily:
        continue
    codes_mp_tc = grp[grp['小程序外卖_val'] > 0]['门店编码'].astype(str).unique().tolist()
    codes_mt_tc = grp[grp['美团_val'] > 0]['门店编码'].astype(str).unique().tolist()
    codes_all_tc = grp[grp['外卖总_val'] > 0]['门店编码'].astype(str).unique().tolist()
    codes_total_tc = grp[grp['有效订单数_val'] > 0]['门店编码'].astype(str).unique().tolist()
    store_daily[date_str].update({
        'mp_tc': codes_mp_tc,
        'mt_tc': codes_mt_tc,
        'all_tc': codes_all_tc,
        'total_tc': codes_total_tc
    })

# 示例：显示第一天各渠道门店数
if store_daily:
    first_day = list(store_daily.keys())[0]
    sd = store_daily[first_day]
    print(f'  {first_day}: 外卖总{len(sd["all"])}家(TC:{len(sd.get("all_tc",[]))}), 自配送{len(sd["mp"])}家(TC:{len(sd.get("mp_tc",[]))}), 美团{len(sd["mt"])}家(TC:{len(sd.get("mt_tc",[]))}), 大盘{len(sd["total"])}家(TC:{len(sd.get("total_tc",[]))})')

# ═══════════════════════════════════════════
# 9. 输出 JSON
# ═══════════════════════════════════════════
print('\n=== 9. 输出 JSON ===')

def clean_nan(obj):
    if isinstance(obj, float) and math.isnan(obj): return None
    if isinstance(obj, dict): return {k: clean_nan(v) for k,v in obj.items()}
    if isinstance(obj, list): return [clean_nan(v) for v in obj]
    return obj

# 门店时段的逐店出餐（供店铺详情弹窗时段热力图）
mp_hourly_by_store = {}
for store_name, grp in df2_valid.groupby('门店名称'):
    ha = grp.groupby('cook_hour')['cook_time_val'].mean().round(1)
    hours = [str(int(h)) for h in range(7, 25)]
    vals = [round(float(ha.get(float(h), 0)), 1) for h in range(7, 25)]
    mp_hourly_by_store[str(store_name)] = {'hours': hours, 'vals': vals}

output = clean_nan({
    'generated_at': str(latest),
    'meituan_date': str(latest),
    'full_date_range': full_date_range,
    'mp_date_range': mp_date_range,
    'mp_daily': mp_daily,
    'mt_daily': mt_daily,
    'perf_daily': perf_daily_list,
    'order_daily': order_daily_list,
    'store_daily': store_daily,
    'dashboard_summary': dashboard_summary,
    'mp_hourly_cook': mp_hourly_cook,
    'mp_hourly_by_store': mp_hourly_by_store,
    'mp_breakdown': mp_breakdown,
    'mp_summary': {
        'total_orders': int(total_valid),
        'total_stores': int(len(agg)),
        'avg_cook_time': round(float(df2_valid['cook_time_val'].mean()), 1) if total_valid > 0 else 0,
        '达标率': round(len(df2_valid[df2_valid['cook_time_val']<=15])/total_valid*100,1) if total_valid>0 else 0,
    },
    'mp_summary_full': {
        'total_orders': int(len(df2)),
    },
    'mt_stores': mt_stores,
    'mp_stores': mp_stores,
    'store_arch': arch_by_code,
    'alerts': alerts,
    'match_summary': {
        'arch_total': len(arch),
        'mt_matched': len(mt_stores),
        'mt_total': len(mt_latest),
        'mp_matched': len(mp_stores),
        'mp_total_7d': len(agg),
        'perf_stores': len(perf_by_code),
        'order_stores': len(order_by_code),
    }
})

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False)

fsize = len(json.dumps(output, ensure_ascii=False)) / 1024
print(f'已输出: {OUT}')
print(f'大小: {fsize:.0f} KB')
print(f'美团门店: {len(mt_stores)} | 小程序门店: {len(mp_stores)} | 预警: {len(alerts)} 条')
