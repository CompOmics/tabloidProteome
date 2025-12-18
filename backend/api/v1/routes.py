import json
import csv
import os
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, aliased
from schemas import Edge, Node, UnimodEntry, UnimodDistinct
from models import EdgeModel, NodeModel, UnimodModel
from config import get_db

local_dir = os.path.dirname(__file__)
print(local_dir)
router = APIRouter()

@router.get('/get-edges', status_code = status.HTTP_200_OK)
def getEdges(db: Session = Depends(get_db)) -> list[Edge]:
    node_a = aliased(NodeModel)
    node_b = aliased(NodeModel)
    stmt = select(
         EdgeModel.score,
         EdgeModel.l_node_a_id,
         EdgeModel.l_node_b_id,
         node_a.composite_name.label('node_a'),
         node_b.composite_name.label('node_b')
    ).join(node_a, EdgeModel.l_node_a_id == node_a.id
    ).join(node_b, EdgeModel.l_node_b_id == node_b.id)
    edges = db.execute(stmt).all()
    return edges

@router.get('/get-nodes', status_code = status.HTTP_200_OK)
def getNodes(db: Session = Depends(get_db)) -> list[Node]:
    nodes = db.scalars(select(NodeModel)).all()
    return nodes

@router.get('/get-unimod', status_code = status.HTTP_200_OK)
def getUnimod(db: Session = Depends(get_db)) -> list[UnimodDistinct]:
    stmt = select(NodeModel.l_unimod_id,
        UnimodModel.unimod_id,
        UnimodModel.full_name,
        UnimodModel.avg_mass,
        UnimodModel.classification
    ).join(UnimodModel, NodeModel.l_unimod_id == UnimodModel.id
    ).distinct()
    unimod = db.execute(stmt).all()
    return unimod
    # nodes = db.scalars(select(NodeModel)).all()
    # return nodes

@router.get('/get-data-edges', status_code = status.HTTP_200_OK)
def getDataEdges():
    # file_path = os.path.join(local_dir, '../../../data/corrs-w-pval.csv')
    file_path = os.path.join(local_dir, '../../data/edges_list.csv')
    # accession node a | accession node b| score | pval | adj_pval
    dataEdges = []
    with open(file_path) as f:
        try:
            csvFile = csv.reader(f)
            for row in csvFile:
                 dataEdges.append(row)
        except json.JSONDecodeError:
                raise HTTPException(status_code=500, detail=f"Error reading file")
    dataNodes = getDataNodes()
    return dataEdges, dataNodes
@router.get('/get-data-nodes', status_code = status.HTTP_200_OK)
def getDataNodes():
    dataList = []
    file_path = os.path.join(local_dir, '../../data/modifications_list_1.csv')
    # unimod_id | code_name | full_name | avg_mass | mono_mass | composition | residue | classification | misc_notes_x | misc_notes_y
    with open(file_path) as f:
        try:
            csvFile = csv.reader(f)
            for row in csvFile:
                 dataList.append(row)
            # dataList = csvFile
        except json.JSONDecodeError:
                raise HTTPException(status_code=500, detail=f"Error reading file")
    return dataList
@router.get('/get-data-modifications', status_code = status.HTTP_200_OK)
def getDataModifications():
    dataList = []
    unimodIdList = []
    file_path = os.path.join(local_dir, '../../data/Unimod_database.csv')
    # unimod_id | code_name | full_name | avg_mass | mono_mass | composition | residue | classification | misc_notes_x | misc_notes_y
    with open(file_path) as f:
        try:
            csvFile = csv.reader(f)
            for row in csvFile:
                if row[0] not in unimodIdList:
                    dataList.append(row)
                    unimodIdList.append(row[0])
            # dataList = csvFile
        except json.JSONDecodeError:
                raise HTTPException(status_code=500, detail=f"Error reading file")
    return dataList
@router.get('/get-data-cytoscape', status_code = status.HTTP_200_OK)
def getDataCytoscape():
    file_path = os.path.join(local_dir, '../../../data/corrs-w-pval.csv')
    # accession node a | accession node b| score | pval | adj_pval
    dataList = []
    with open(file_path) as f:
        try:
            csvFile = csv.reader(f)
            index = 0
            for row in csvFile:
                 print(row)
                 if index > 0 and float(row[2]) > 0.7:
                    node1 = { 'data': {'id': row[0]}}
                    node2 = {'data': {'id': row[1]}}
                    dataList.append(node1)
                    dataList.append(node2)
                    edge = {'data': {'id': row[0] + row[1], 'source': row[0], 'target': row[1]}}
                    dataList.append(edge)
                 index = index+1
        except json.JSONDecodeError:
                raise HTTPException(status_code=500, detail=f"Error reading file")
    return dataList