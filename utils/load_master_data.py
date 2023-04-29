import pandas as pd
from sqlalchemy import create_engine
import sys

HOST='RDS_HOST_GOES_HERE'
PORT='5432'
DATABASE='RDS_DB_GOES_HERE'
USER='RDS_USER_GOES_HERE'
PASSWORD='RDS_PW_GOES_HERE'
SQLALCHEMY_DATABASE_URI = f"postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}"

try:
    engine = create_engine(SQLALCHEMY_DATABASE_URI)
    for file in reversed(sys.argv[1:]):
        print(f"Loading {file}")
        master = pd.read_csv(file, encoding='latin_1', delimiter='\t', dtype=object)
        master.to_sql('dmd_master_data', engine, if_exists='append', index=False)

except:
    print("Exception!")
