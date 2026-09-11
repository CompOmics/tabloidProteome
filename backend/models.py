"""SQLAlchemy models for optional persistence of CSV-backed data.

These models are small and intentionally conservative — the project currently reads CSV files
directly and does not require a database. These models make it easy to add a DB later.
"""
from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


class EdgeModel(Base):
    __tablename__ = "edges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    l_node_a_id = Column(Integer, ForeignKey('nodes.id'), index=True, nullable=False)
    l_node_b_id = Column(Integer, ForeignKey('nodes.id'), index=True, nullable=False)
    score = Column(Float, index=True, nullable=True)
    qvalue = Column(Float, nullable=True)
    same_protein = Column(Integer, nullable=True)
    same_site = Column(Integer, nullable=True)
    position_gap = Column(Integer, nullable=True)
    same_mod = Column(Integer, nullable=True)
    shared_peptide = Column(Integer, nullable=True)


class NodeModel(Base):
    __tablename__ = "nodes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    composite_name = Column(String, index=True, nullable=True)
    composite_gene_name = Column(String, index=True, nullable=True)
    accession = Column(String, index=True, nullable=False)
    entry_name = Column(String, index=True, nullable=True)
    gene_name = Column(String, index=True, nullable=True)
    position = Column(String, index=True, nullable=True)
    residue = Column(String, index=True, nullable=True)
    l_unimod_id = Column(Integer, ForeignKey('unimod.id'), index=True, nullable=True)


class UnimodModel(Base):
    __tablename__ = "unimod"

    id = Column(Integer, primary_key=True, autoincrement=True)
    unimod_id = Column(String, index=True, nullable=False)
    code_name = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    avg_mass = Column(Float, nullable=True)
    mono_mass = Column(Float, nullable=True)
    classification = Column(String, nullable=True)
