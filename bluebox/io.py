import pandas as pd


def load(name):
    """Read a fixed column width text file of timeline items.
    """
    df = pd.read_csv(name, sep='|')
    # Remove whitespace from column names.
    df.rename(lambda n: n.strip(), axis=1, inplace=True)
    # Strip whitespace from string column values.
    for col in df.select_dtypes('object'):
        df[col] = df[col].apply(lambda t: t.strip() if isinstance(t, str) else '')
    # Ensure that required columns are numeric.
    for col in 'start', 'duration', 'ramp_up', 'ramp_down':
        df[col] = pd.to_numeric(df[col]).fillna(0)
    if df.dtypes['row'] != 'object':
        df['row'] = [''] * len(df)
    return df


def save(df, name, padding=2):
    """Write timeline items to a fixed column width text file.
    """
    # Get the max width of the values in each column.
    colwidth = {col: max([len(str(value)) for value in df[col]] + [len(col)]) + padding for col in df.columns}
    def pad(t, s):
        t = str(t) if t != 0 else ''
        return ' ' + t + (' ' * (s - len(t)))
    # Convert each column to padded string values.
    for col in df.columns:
        df[col] = df[col].apply(lambda t: pad(t, colwidth[col]))
    # Pad each column name.
    df.rename(lambda n: pad(n, colwidth[n]), axis=1, inplace=True)
    csv = df.to_csv(index=False, sep='|')
    with open(name, 'w') as f:
        print(csv, file=f)
