import csv
import logging
from sqlalchemy import create_engine, select, and_
from sqlalchemy.orm import Session
from config import config_uri
from models import Base, EdgeModel, NodeModel, UnimodModel
import pandas as pd

database_uri = config_uri()
engine = create_engine(database_uri)
unimod_dict = {}
nodes_dict = {}

DATA_URL = 'data/'

def recreate_database():
    logging.info('recreate database')
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

def insert_unimod():
    print('read unimod')
    session = Session(engine)
    existing_unimod = []
    df_unimod = pd.read_csv(DATA_URL + 'Unimod_database.csv')
    try:
        for row in df_unimod.itertuples():
            if row.unimod_id in existing_unimod:
                continue
            else:
                existing_unimod.append(row.unimod_id)
                unimod_entry = UnimodModel(
                    unimod_id=row.unimod_id,
                    code_name=row.code_name,
                    full_name=row.full_name,
                    avg_mass=row.avg_mass,
                    mono_mass=row.mono_mass,
                    classification=row.classification
                )
                session.add(unimod_entry)
                session.flush()  # To get the id before commit
                unimod_dict[row.unimod_id] = unimod_entry.id
    except Exception as e:
        session.rollback()
        logging.error(e)
        raise Exception
    else:
        print('insert unimod')
        session.commit()


def insert_nodes():
    print('read nodes')
    session = Session(engine)
    df_nodes = pd.read_csv(DATA_URL + 'modifications_list_1.csv')
    try:
        for row in df_nodes.itertuples():
            node = NodeModel(
                composite_name=row.PTM_ID,
                accession=row.Gene,
                entry_name=row.EntryName,
                gene_name=row.GeneName,
                position=row.POS,
                residue=row.RES,
                l_unimod_id=unimod_dict.get(row.MOD)
            )
            session.add(node)
            session.flush()  # To get the id before commit
            nodes_dict[row.PTM_ID] = node.id
    except Exception as e:
        session.rollback()
        logging.error(e)
        raise Exception
    else:
        print('insert nodes')
        session.commit()

def insert_edges():
    print('read edges')
    session = Session(engine)
    df_edges = pd.read_csv(DATA_URL + 'edges_list.csv')
    try:
        for row in df_edges.itertuples():
            edge = EdgeModel(
                l_node_a_id=nodes_dict.get(row.nodeA),
                l_node_b_id=nodes_dict.get(row.nodeB),
                score=row.Score,
                pval=row.pval,
                adj_pval=row.adj_pval
            )
            session.add(edge)
    except Exception as e:
        session.rollback()
        logging.error(e)
        raise Exception
    else:
        print('insert edges')
        session.commit()

if __name__ == '__main__':
    recreate_database()
    insert_unimod()
    insert_nodes()
    insert_edges()