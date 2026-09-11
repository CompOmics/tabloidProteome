from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased
from schemas import Edge, Node, UnimodEntry, UnimodDistinct
from models import EdgeModel, NodeModel, UnimodModel
from config import get_db

router = APIRouter()

@router.get('/get-edges', status_code = status.HTTP_200_OK)
def getEdges(min_score: float = 0.6, db: Session = Depends(get_db)) -> list[Edge]:
    node_a = aliased(NodeModel)
    node_b = aliased(NodeModel)
    stmt = select(
         EdgeModel.score,
         EdgeModel.l_node_a_id,
         EdgeModel.l_node_b_id,
         node_a.composite_name.label('node_a'),
         node_b.composite_name.label('node_b'),
         EdgeModel.qvalue,
         EdgeModel.same_protein,
         EdgeModel.same_site,
         EdgeModel.position_gap,
         EdgeModel.same_mod,
         EdgeModel.shared_peptide,
    ).join(node_a, EdgeModel.l_node_a_id == node_a.id
    ).join(node_b, EdgeModel.l_node_b_id == node_b.id
    ).where(EdgeModel.score >= min_score)
    edges = db.execute(stmt).all()
    return edges

@router.get('/get-edges-count', status_code = status.HTTP_200_OK)
def getEdgesCount(min_score: float = 0.6, max_score: float = 1.0, db: Session = Depends(get_db)) -> int:
    stmt = select(func.count()).select_from(EdgeModel).where(
        EdgeModel.score >= min_score, EdgeModel.score <= max_score
    )
    return db.execute(stmt).scalar()

@router.get('/get-nodes', status_code = status.HTTP_200_OK)
def getNodes(db: Session = Depends(get_db)) -> list[Node]:
    stmt = select(
        NodeModel.id,
        NodeModel.composite_name,
        NodeModel.composite_gene_name,
        NodeModel.accession,
        NodeModel.entry_name,
        NodeModel.gene_name,
        NodeModel.position,
        NodeModel.residue,
        UnimodModel.unimod_id,
        UnimodModel.full_name,
    ).join(UnimodModel, NodeModel.l_unimod_id == UnimodModel.id)
    nodes = db.execute(stmt).all()
    return nodes

@router.get('/get-unimod', status_code = status.HTTP_200_OK)
def getUnimod(db: Session = Depends(get_db)) -> list[UnimodDistinct]:
    stmt = select(
        UnimodModel.unimod_id,
        UnimodModel.full_name,
        UnimodModel.avg_mass,
        UnimodModel.classification
    ).join(NodeModel, NodeModel.l_unimod_id == UnimodModel.id
    ).distinct()
    unimod = db.execute(stmt).all()
    return unimod

@router.get('/get-nodes-test', status_code = status.HTTP_200_OK)
def getNodesTest(db: Session = Depends(get_db)) -> list[Node]:
    """Get first 20 nodes for testing"""
    stmt = select(
        NodeModel.id,
        NodeModel.composite_name,
        NodeModel.composite_gene_name,
        NodeModel.accession,
        NodeModel.entry_name,
        NodeModel.gene_name,
        NodeModel.position,
        NodeModel.residue,
        UnimodModel.unimod_id,
        UnimodModel.full_name,
    ).join(UnimodModel, NodeModel.l_unimod_id == UnimodModel.id
    ).limit(20)
    nodes = db.execute(stmt).all()
    # Convert to plain dicts to ensure JSON serializability
    result = []
    for node in nodes:
        result.append({
            "id": node.id,
            "composite_name": node.composite_name or "",
            "composite_gene_name": node.composite_gene_name or "",
            "accession": node.accession or "",
            "entry_name": node.entry_name or "",
            "gene_name": node.gene_name or "",
            "position": node.position or "",
            "residue": node.residue or "",
            "unimod_id": node.unimod_id or "",
            "full_name": node.full_name or "",
        })
    return result

@router.get('/get-edges-test', status_code = status.HTTP_200_OK)
def getEdgesTest(db: Session = Depends(get_db)) -> list[Edge]:
    """Get edges connecting first 20 nodes"""
    # Get first 20 nodes
    first_nodes = db.scalars(select(NodeModel.id).limit(20)).all()
    
    if not first_nodes:
        return []
    
    # Get edges where both endpoints are in the first 20 nodes
    node_a = aliased(NodeModel)
    node_b = aliased(NodeModel)
    stmt = select(
         EdgeModel.score,
         EdgeModel.l_node_a_id,
         EdgeModel.l_node_b_id,
         node_a.composite_name.label('node_a'),
         node_b.composite_name.label('node_b')
    ).join(node_a, EdgeModel.l_node_a_id == node_a.id
    ).join(node_b, EdgeModel.l_node_b_id == node_b.id
    ).where(EdgeModel.l_node_a_id.in_(first_nodes)
    ).where(EdgeModel.l_node_b_id.in_(first_nodes))
    
    edges = db.execute(stmt).all()
    # Convert to plain dicts to ensure JSON serializability
    result = []
    for edge in edges:
        result.append({
            "score": float(edge.score) if edge.score is not None else 0.0,
            "l_node_a_id": edge.l_node_a_id,
            "l_node_b_id": edge.l_node_b_id,
            "node_a": edge.node_a or "",
            "node_b": edge.node_b or "",
        })
    return result