"""Pydantic schemas for CSV-backed resources.

Notes / assumptions:
- MoDPA edges CSV columns: pair_key, Score, qvalue, nodeA, nodeB, protA, posA, resA, unimodA,
  protB, posB, resB, unimodB, same_protein, same_site, position_gap, same_mod, shared_peptide
- MoDPA nodes CSV columns: name, UniAcc, Entry, Gene, POS, RES, PTM, UniModID
- `Unimod_database.csv` rows follow: unimod_id, code_name, full_name, avg_mass, mono_mass, composition, residue, classification, misc_notes_x, misc_notes_y

These schemas are minimal and used for validation/typing when converting CSV rows to structured objects.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class Edge(BaseModel):
    """Schema for an edge row from the MoDPA edges CSV."""
    score: float
    l_node_a_id: int
    l_node_b_id: int
    node_a: str
    node_b: str
    qvalue: Optional[float] = None
    same_protein: Optional[int] = None
    same_site: Optional[int] = None
    position_gap: Optional[int] = None
    same_mod: Optional[int] = None
    shared_peptide: Optional[int] = None

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
    unimod_id: str
    full_name: Optional[str] = None

    model_config = {"extra": "ignore"}

class UnimodDistinct(BaseModel):
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

