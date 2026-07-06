import openpyxl, sys
sys.stdout.reconfigure(encoding='utf-8')

OLD_PATH = 'data_sources/OLD.xlsx'
NEW_PATH = 'data_sources/NEW.xlsx'

for path, label in [(OLD_PATH, 'OLD'), (NEW_PATH, 'NEW')]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=False)
    ws = wb['美团指标数据源']
    header = list(next(ws.iter_rows(min_row=1, max_row=1, values_only=True)))
    wb.close()
    
    print(f'\n=== {label} ({path}) ===')
    print(f'Total cols: {len(header)}')
    print(f'Header: {header[:50]}')
    
    # Check key columns
    for key in ['日期', '门店名称', '门店名称.1', '门店id', '门店编码', '品牌', '市场', '城市', '大区', '区域', '大店']:
        idx = header.index(key) if key in header else 'NOT FOUND'
        print(f'  {key}: col {idx}')
