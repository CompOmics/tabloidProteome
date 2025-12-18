export interface Node {
    composite_name: string
    entry_name: string
    gene_name: string
    accession: string
    position: number
    residue: string
    l_unimod_id: number
}
export interface Edge {
    score: number
    l_node_a: number
    l_node_b: number
    node_a: string
    node_b: string
}
export interface Unimod {
    l_unimod_id: number
    name: string
    mass: number
    formula: string,
    title: string
}