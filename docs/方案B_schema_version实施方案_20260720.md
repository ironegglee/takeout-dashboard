# 方案B · schema_version 数据驱动实施方案

> 状态：方案文档，待确认后实施
> 前提：7月数据源暂未有 资质核验得分 / 后厨环境核验得分 列，当前 SCHEMA = "v1"
> 目标：gen 探测数据源列 → data.json 标记 → 前端按版本自动选模板

---

## 一、数据契约变化

### 当前 data.json（v1）

```json
{
  "generated_at": "2026-07-20",
  "meituan_date": "...",
  "mt_stores": [
    {
      "shop_dims": {
        "peak_hours": 95, "quality_rate": 92,
        "reject_rate": 88,   // 旧指标——已下线
        "reply_rate": 76,     // 旧指标——已下线
        "merchant_rating": 90, "menu_rich": 85,
        "decor_rich": 80, "service_rich": 82,
        "cook_report": 93, "base_hours": 96
      }
    }
  ],
  "mt_daily": [...],
  "alerts": [...]
}
```

### 改造后 data.json（新增 mt_schema_version）

```json
{
  "mt_schema_version": "v2",    // 新增顶层字段
  "generated_at": "2026-07-20",
  "meituan_date": "...",
  "mt_stores": [
    {
      "shop_dims": {
        "peak_hours": 95, "quality_rate": 92,
        "cert_verify": 73,      // 新指标：资质核验得分（v2 才有）
        "kitchen_env": 68,       // 新指标：后厨环境核验得分（v2 才有）
        "merchant_rating": 90, "menu_rich": 85,
        "decor_rich": 80, "service_rich": 82,
        "cook_report": 93, "base_hours": 96
      }
    }
  ],
  ...
}
```

**核心规则**：
- `mt_schema_version` = `"v1"`：shop_dims 含 `reject_rate` + `reply_rate`（当前）
- `mt_schema_version` = `"v2"`：shop_dims 含 `cert_verify` + `kitchen_env`（新）
- 两种 schema **互斥**，不会同时包含新旧指标
- mt_daily、alerts、exp_dims 不受影响

---

## 二、gen_data_v4.py 改造（预估 ~20 行改动）

### 2.1 新增 schema 探测函数

```python
# 在 dim_labels 定义之前（约第335行）插入
def detect_schema(mt_header_idx):
    """探测美团数据源指标列版本
    v1: 含 商家不接单率得分 + 差评回复率得分（当前）
    v2: 含 资质核验得分 + 后厨环境核验得分（美团新评分体系）
    判定标准：两个新列同时存在 → v2；否则 v1
    """
    header_names = [k.strip() for k in mt_header_idx.keys()]
    has_cert = '资质核验得分' in header_names
    has_kitchen = '后厨环境核验得分' in header_names
    return 'v2' if (has_cert and has_kitchen) else 'v1'
```

### 2.2 dim_labels 拆为 V1/V2 两套

```python
# 原 dim_labels（行 336-342）→ 改名为 dim_labels_v1，不变
dim_labels_v1 = {
    'peak_hours': '高峰营业时长得分', 'quality_rate': '优质商品率得分',
    'reject_rate': '商家不接单率得分', 'reply_rate': '差评回复率得分',
    'merchant_rating': '商家评分得分', 'menu_rich': '菜单丰富度得分',
    'decor_rich': '装修丰富度得分', 'service_rich': '服务功能丰富度得分',
    'cook_report': '出餐完成上报率得分/配送准时率得分', 'base_hours': '基础营业时长得分'
}

dim_labels_v2 = {
    'peak_hours': '高峰营业时长得分', 'quality_rate': '优质商品率得分',
    'cert_verify': '资质核验得分', 'kitchen_env': '后厨环境核验得分',
    'merchant_rating': '商家评分得分', 'menu_rich': '菜单丰富度得分',
    'decor_rich': '装修丰富度得分', 'service_rich': '服务功能丰富度得分',
    'cook_report': '出餐完成上报率得分/配送准时率得分', 'base_hours': '基础营业时长得分'
}
```

### 2.3 mt_stores 中 shop_dims 按 schema 分支

```python
# 在构建 mt_stores 之前（约第395行）插入
MT_SCHEMA = detect_schema(mt_header_idx)
dim_labels = dim_labels_v2 if MT_SCHEMA == 'v2' else dim_labels_v1
print(f'  美团指标 Schema: {MT_SCHEMA}')

# shop_dims 构建（约第405行）改为：
shop_dims = {
    'peak_hours': safe_float(col_val(row, mt_header_idx, '高峰营业时长得分')),
    'quality_rate': safe_float(col_val(row, mt_header_idx, '优质商品率得分')),
    'merchant_rating': safe_float(col_val(row, mt_header_idx, '商家评分得分')),
    'menu_rich': safe_float(col_val(row, mt_header_idx, '菜单丰富度得分')),
    'decor_rich': safe_float(col_val(row, mt_header_idx, '装修丰富度得分')),
    'service_rich': safe_float(col_val(row, mt_header_idx, '服务功能丰富度得分')),
    'cook_report': safe_float(col_val(row, mt_header_idx, '出餐完成上报率得分/配送准时率得分')),
    'base_hours': safe_float(col_val(row, mt_header_idx, '基础营业时长得分')),
}
if MT_SCHEMA == 'v2':
    shop_dims['cert_verify'] = safe_float(col_val(row, mt_header_idx, '资质核验得分'))
    shop_dims['kitchen_env'] = safe_float(col_val(row, mt_header_idx, '后厨环境核验得分'))
else:
    shop_dims['reject_rate'] = get_valid_score(code, '商家不接单率得分')
    shop_dims['reply_rate'] = get_valid_score(code, '差评回复率得分')
```

### 2.4 预警循环改 dim_labels 引用 + 子维度列表

```python
# 店铺分预警（约第800行）—— dim_names 列表改为动态
if MT_SCHEMA == 'v2':
    alert_dim_names = ['peak_hours','quality_rate','cert_verify','kitchen_env','merchant_rating',
                       'menu_rich','decor_rich','service_rich','cook_report','base_hours']
else:
    alert_dim_names = ['peak_hours','quality_rate','reject_rate','reply_rate','merchant_rating',
                       'menu_rich','decor_rich','service_rich','cook_report','base_hours']

for dim_name in alert_dim_names:
    ...
```

### 2.5 data.json 输出加顶层字段

```python
# output 中（约第981行）插入
output = clean_nan({
    'mt_schema_version': MT_SCHEMA,   # 新增
    'generated_at': str(latest_mt_date),
    ...
})
```

---

## 三、dashboard/index.html 改造（预估 ~200 行改动）

### 3.1 DIM_META 拆为 V1/V2

```javascript
// 原 DIM_META（行 2347）➔ DIM_META_V1（内容不变，去掉 reject_rate 和 reply_rate 其实不用去，因为 V1 就是旧的）
// 实际上：保留原 DIM_META 不动，改名为 DIM_META_V1
// 新增 DIM_META_V2，把 reject_rate/reply_rate 条目替换为：
var DIM_META_V2 = {
  '资质核验得分': {cat:'shop',field:'cert_verify',def:'...',calc:'...',source:'美团商家后台—店铺分—资质核验',tips:[...],target:95,max:100},
  '后厨环境核验得分': {cat:'shop',field:'kitchen_env',def:'...',calc:'...',source:'美团商家后台—店铺分—后厨环境核验',tips:[...],target:95,max:100},
  // ... 其余 8 个不变（从 DIM_META_V1 复制）
};
```

### 3.2 启动时选模板

```javascript
// 在 applyRealData() 或数据加载之后（约第3600行附近）
var SCHEMA = embedded_data.mt_schema_version || 'v1';
var DIM_META = SCHEMA === 'v2' ? DIM_META_V2 : DIM_META_V1;
var ALERT_DIMS = SCHEMA === 'v2'
  ? ['cert_verify','kitchen_env','merchant_rating','menu_rich','decor_rich','service_rich','cook_report','peak_hours','quality_rate','base_hours']
  : ['reject_rate','reply_rate','merchant_rating','menu_rich','decor_rich','service_rich','cook_report','peak_hours','quality_rate','base_hours'];
```

### 3.3 涉及改动的 UI 区域

| 区域 | 所在行附近 | 改动方式 |
|------|-----------|---------|
| **概览区 · 店铺分下钻树** | 概览卡片内的维度列表 | 按 SCHEMA 选 dim_label 映射，V2 显示 cert_verify + kitchen_env |
| **门店详情抽屉 ×2** | 两处门店详情弹窗，各 20-30 行 | 按 SCHEMA 选 shop_dims 字段渲染，V2 用 cert_verify/kitchen_env |
| **下钻表格** | drillDim 函数（行2362） | DIM_META 已在启动时选定，drillDim 自动适配 |
| **预警面板** | 预警行渲染区域 | alert loop 读 dim_label 时已适配（DIM_META 已选） |
| **applyRealData** | 约第3600行 | 嵌入数据读取映射表按 SCHEMA 选 |

### 3.4 调试入口（URL 参数）

```javascript
// 启动时
var forceSchema = (window.location.search||'').match(/[?&]force=(v[12])/);
if(forceSchema) {
  SCHEMA = forceSchema[1];
  console.log('[DEBUG] 强制 Schema:', SCHEMA);
}
// 用法：index.html?force=v1  或  index.html?force=v2
```

---

## 四、实施步骤

| 步骤 | 内容 | 预估 |
|------|------|------|
| 1 | gen_data_v4.py：新增 detect_schema + dim_labels V2 + shop_dims 分支 | ~20行 |
| 2 | gen_data_v4.py：预警循环 dim_names 动态化 + output 加 mt_schema_version | ~10行 |
| 3 | gen_data_v4.py：本地运行验证，确认输出 data.json 含 mt_schema_version:"v1" | 2分钟 |
| 4 | index.html：DIM_META 拆 V1/V2，启动选模板 | ~60行 |
| 5 | index.html：概览树 + 详情抽屉 ×2 + applyRealData 按 SCHEMA 分支 | ~120行 |
| 6 | index.html：调试入口 force=v1/v2 | ~10行 |
| 7 | 本地构建 embed → 打开 index.html 验证 V1 模式无变化 | 3分钟 |
| 8 | ?force=v2 验证 V2 模式布局正确（指标名替换） | 3分钟 |
| 9 | V2 模式下资质核验/后厨环境全部显 "--"（数据源缺列）—— 预期行为 | — |

---

## 五、过渡期处理策略

### 现在 → 美团出新列前

```
SCHEMA = "v1"（gen 探测不到新列）
  → data.json.mt_schema_version = "v1"
  → 前端选 DIM_META_V1 模板
  → 看板与现状完全一致，改动期间不影响线上
```

### 美团出新列当天

```
SCHEMA = "v2"（gen 探测到资质核验+后厨环境列）
  → data.json.mt_schema_version = "v2"
  → 前端选 DIM_META_V2 模板
  → 新 UI 自动生效，无需人工干预
```

### 紧急回退

如果 V2 模板有问题：
- 让 gen 临时强制输出 v1（加一行 `MT_SCHEMA = 'v1'`）
- 或用 `?force=v1` 参数在前端临时降级

---

## 六、决策点汇总（均按默认建议）

| # | 决策项 | 默认值 | 说明 |
|---|--------|--------|------|
| 1 | 两列都存在才升级 | a ✓ | 任一不够，必须同时有 |
| 2 | V2 弃用旧指标 | a ✓ | 不保留 reject_rate/reply_rate |
| 3 | 加调试入口 | a ✓ | URL 参数 ?force=v1/v2 |
| 4 | 预警规则同步升级 | 暂用现有阈值 | V2 预警阈值后续单独讨论 |

---

## 七、注意事项

1. **V2 模式下新指标全部为 0**：数据源暂未导出新列，V2 在线上启用前需要美团更新导出格式
2. **gen 不推 GitHub 即可本地验证**：本地跑 gen_data_v4.py 看 data.json 输出，再跑 embed_data.py 看 index.html 效果
3. **改动不影响 V1 路径**：代码改完之后 V1 渲染结果应与改之前完全一致，这是验收标准
