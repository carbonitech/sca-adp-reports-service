import io
import pandas


def convert_to_dfs(data: bytes) -> dict[str,pandas.DataFrame]:
    
    result = {}
    excel_file = pandas.ExcelFile(io.BytesIO(data))
    for sheet in excel_file.sheet_names:
        if sheet == 'Open Orders':
            result[sheet] = excel_file.parse(sheet, skiprows=6)
        elif sheet == 'Shipments':
            result[sheet] = excel_file.parse(sheet, skiprows=5)
    return result


def convert_to_bytes(dfs: dict[str,pandas.DataFrame]) -> bytes:

    bytes_file = io.BytesIO()
    with pandas.ExcelWriter(bytes_file) as file:
        for sheet, df in dfs.items():
            df.to_excel(file, sheet, index=False)
            
    bytes_file.seek(0)
    return bytes_file.read()

    
def remove_extra_rows(df: pandas.DataFrame) -> pandas.DataFrame:
    
    new_df = df.copy()

    new_df.dropna(subset=['Description'], inplace=True)
    dup_header_row_filter = new_df['Description'] != 'Description'
    new_df = new_df[dup_header_row_filter]

    return new_df


def format_dfs(dfs: dict[str,pandas.DataFrame]) -> dict[str,pandas.DataFrame]:
    return {name: remove_extra_rows(df) for name, df in dfs.items()}


def format_tables(data: bytes) -> bytes:
    dfs = convert_to_dfs(data)
    formatted_dfs = format_dfs(dfs)
    return convert_to_bytes(formatted_dfs)
    
