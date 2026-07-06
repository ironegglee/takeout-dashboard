import openpyxl, sys, time
sys.stdout.reconfigure(encoding='utf-8')

for path, label in [('data_sources/OLD.xlsx', 'OLD'), ('data_sources/NEW.xlsx', 'NEW')]:
    start = time.time()
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb['小程序配送数据源']
    count = 0
    for row in ws.iter_rows(min_row=2):
        count += 1
    wb.close()
    t = time.time() - start
    print(f'{label} 配送数据: {count} rows, {t:.1f}s')
