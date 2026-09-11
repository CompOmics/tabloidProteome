import logging
import pandas as pd
from sqlalchemy import create_engine, select, insert
from sqlalchemy.orm import Session
from config import Settings, config_uri
from models import Base, EdgeModel, NodeModel, UnimodModel

logging.basicConfig(level=logging.INFO)

# crud.py writes to the database being (re)built, which is deliberately kept
# separate from the app's read-only `.env` (see backend/.env.crud).
crud_settings = Settings(_env_file='.env.crud')
database_uri = config_uri(crud_settings)
engine = create_engine(database_uri)

# Unimod is a stable reference table, not part of a dated data drop, so it's
# always read from the repo's own data/ dir regardless of DATA_DIR.
UNIMOD_DIR = 'data/'
UNIMOD_FILE = 'Unimod_database.csv'

DATA_DIR = crud_settings.DATA_DIR
NODES_FILE = '20260902-MoDPA-nodes.csv'
EDGES_FILE = '20260902-MoDPA-edges.csv'

EDGE_CHUNK_SIZE = 100_000


def recreate_database():
    logging.info('recreate database')
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def insert_unimod():
    logging.info('read unimod')
    df = pd.read_csv(UNIMOD_DIR + UNIMOD_FILE)
    df = df.drop_duplicates(subset='unimod_id', keep='first')
    records = [
        {
            'unimod_id': str(row['unimod_id']),
            'code_name': row['code_name'],
            'full_name': row['full_name'],
            'avg_mass': row['avg_mass'],
            'mono_mass': row['mono_mass'],
            'classification': row['classification'],
        }
        for row in df.to_dict('records')
    ]
    logging.info('insert unimod (%d rows)', len(records))
    with engine.begin() as conn:
        conn.execute(insert(UnimodModel.__table__), records)


def insert_nodes():
    logging.info('read nodes')
    with Session(engine) as session:
        unimod_dict = dict(session.execute(select(UnimodModel.unimod_id, UnimodModel.id)).all())

    df = pd.read_csv(DATA_DIR + NODES_FILE)
    records = [
        {
            'composite_name': row['name'],
            'composite_gene_name': f"{row['Gene']}|{row['POS']}|{row['RES']}|{row['UniModID']}",
            'accession': row['UniAcc'],
            'entry_name': row['Entry'],
            'gene_name': row['Gene'],
            'position': str(row['POS']),
            'residue': row['RES'],
            'l_unimod_id': unimod_dict.get(str(row['UniModID'])),
        }
        for row in df.to_dict('records')
    ]
    logging.info('insert nodes (%d rows)', len(records))
    with engine.begin() as conn:
        conn.execute(insert(NodeModel.__table__), records)


def insert_edges():
    logging.info('read edges')
    with Session(engine) as session:
        nodes_dict = dict(session.execute(select(NodeModel.composite_name, NodeModel.id)).all())

    bool_cols = ['same_protein', 'same_site', 'same_mod', 'shared_peptide']
    total = 0
    with engine.begin() as conn:
        for chunk in pd.read_csv(DATA_DIR + EDGES_FILE, chunksize=EDGE_CHUNK_SIZE):
            for col in bool_cols:
                chunk[col] = chunk[col].astype(int)

            records = [
                {
                    'l_node_a_id': nodes_dict.get(row['nodeA']),
                    'l_node_b_id': nodes_dict.get(row['nodeB']),
                    'score': row['Score'],
                    'qvalue': row['qvalue'],
                    'same_protein': row['same_protein'],
                    'same_site': row['same_site'],
                    'position_gap': None if pd.isna(row['position_gap']) else int(row['position_gap']),
                    'same_mod': row['same_mod'],
                    'shared_peptide': row['shared_peptide'],
                }
                for row in chunk.to_dict('records')
            ]
            conn.execute(insert(EdgeModel.__table__), records)
            total += len(records)
            logging.info('inserted %d edges', total)


if __name__ == '__main__':
    recreate_database()
    insert_unimod()
    insert_nodes()
    insert_edges()
