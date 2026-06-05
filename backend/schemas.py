"""Pydantic schemas for CSV-backed resources.

Notes / assumptions:
- `edges_list.csv` rows are expected as: node_a, node_b, score, pval, adj_pval
- `modifications_list_1.csv` rows (nodes) are expected to include at least: accession, protein, position, residue, modification
- `Unimod_database.csv` rows follow: unimod_id, code_name, full_name, avg_mass, mono_mass, composition, residue, classification, misc_notes_x, misc_notes_y

These schemas are minimal and used for validation/typing when converting CSV rows to structured objects.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class Edge(BaseModel):
    """Schema for an edge row from `edges_list.csv`.

    Fields map to CSV columns: node_a, node_b, score, pval, adj_pval
    """
    score: float
    l_node_a_id: int
    l_node_b_id: int
    node_a: str
    node_b: str
    # pval: Optional[float] = None
    # adj_pval: Optional[float] = None

    model_config = {
        "extra": "ignore",
        "populate_by_name": True,
    }


class Node(BaseModel):
    id: int
    composite_name: str
    composite_gene_name: str
    accession: str
    entry_name: str
    gene_name: str
    position: Optional[str] = None
    residue: Optional[str] = None
    l_unimod_id: int

    model_config = {"extra": "ignore"}

class UnimodDistinct(BaseModel):
    l_unimod_id: int
    unimod_id: str
    full_name: Optional[str] = None
    avg_mass: Optional[float] = None
    classification: Optional[str] = None

    model_config = {"extra": "ignore"}

class UnimodEntry(BaseModel):
    """Schema for a Unimod database row (`Unimod_database.csv`)."""

    unimod_id: str
    code_name: Optional[str] = None
    full_name: Optional[str] = None
    avg_mass: Optional[float] = None
    mono_mass: Optional[float] = None
    classification: Optional[str] = None

    model_config = {"extra": "ignore"}

