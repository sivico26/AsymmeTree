# -*- coding: utf-8 -*-

"""
Construction of Least Resolved Trees (LRT).

Computes an LRT from a (not necessarily valid) cBMG or
from an observable gene tree.
"""

import itertools

import networkx as nx

from asymmetree.best_matches.TrueBMG import bmg_from_tree
from asymmetree.tools.PhyloTree import PhyloTree, PhyloTreeNode
from asymmetree.tools.GraphTools import sort_by_colors, is_properly_colored
from asymmetree.tools.Build import Build


__author__ = 'David Schaller'


def informative_triples(graph, color_dict=None):
    """Compute the informative triples of a colored digraph."""
    
    if not isinstance(graph, nx.DiGraph):
        raise TypeError("must be a NetworkX 'Digraph'")
    
    if not color_dict:
        color_dict = sort_by_colors(graph)
    
    R = []
    
    for c1, c2 in itertools.permutations(color_dict.keys(), 2):
        for a in color_dict[c1]:
            for b1, b2 in itertools.permutations(color_dict[c2], 2):
                if graph.has_edge(a, b1) and (not graph.has_edge(a, b2)):
                    R.append( (a, b1, b2) )
    
    return R


def forbidden_triples(graph, color_dict=None):
    """Compute the forbidden triples of a colored digraph."""
    
    if not isinstance(graph, nx.DiGraph):
        raise TypeError("must be a NetworkX 'Digraph'")
    
    if not color_dict:
        color_dict = sort_by_colors(graph)
    
    F = []
    
    for c1, c2 in itertools.permutations(color_dict.keys(), 2):
        for a in color_dict[c1]:
            for b1, b2 in itertools.combinations(color_dict[c2], 2):
                if graph.has_edge(a, b1) and graph.has_edge(a, b2):
                    F.append( (a, b1, b2) )
    
    return F


def informative_forbidden_triples(graph, color_dict=None):
    """Compute the informative and forbidden triples of a colored digraph."""
    
    if not isinstance(graph, nx.DiGraph):
        raise TypeError("must be a NetworkX 'Digraph'")
    
    if not color_dict:
        color_dict = sort_by_colors(graph)
    
    R, F = [], []
    
    for c1, c2 in itertools.permutations(color_dict.keys(), 2):
        for a in color_dict[c1]:
            for b1, b2 in itertools.combinations(color_dict[c2], 2):
                
                if graph.has_edge(a, b1) and graph.has_edge(a, b2):
                    F.append( (a, b1, b2) )
                elif graph.has_edge(a, b1):
                    R.append( (a, b1, b2) )
                elif graph.has_edge(a, b2):
                    R.append( (a, b2, b1) )
    
    return R, F    


# --------------------------------------------------------------------------
#                      LRT FROM OBSERVABLE GENE TREE
# --------------------------------------------------------------------------

def lrt_from_observable_tree(T):
    """Computes the Least Resolved Tree from a tree.
    
    The unique Least Resolved Tree from a leaf-colored (observable)
    gene tree is computed by contraction of all redundant edges.
    """
    
    lrt = T.copy()
    if not lrt.root:
        return lrt
    
    # remove planted root if existent
    lrt.remove_planted_root()
    
    # assign list of leaves to each node
    lrt.supply_leaves()
    
    subtree_colors = {}
    for v in lrt.preorder():
        subtree_colors[v] = {leaf.color for leaf in v.leaves}
        
    arc_colors = _arc_colors(lrt, subtree_colors)
    red_edges = redundant_edges(lrt, subtree_colors, arc_colors)
    lrt.contract(red_edges)
    lrt = lrt.topology_only()
    
    return lrt


def _arc_colors(T, subtree_colors):
    """Color sets relevant for redundant edge computation.
    
    Computes for all inner vertices v the color set of y such that y with (x,y)
    is an arc in the BMG and lca(x,y) = v.
    """
    
    all_colors = subtree_colors[T.root]
    
    arc_colors = {v: set() for v in T.preorder()}     # color sets for all v
    
    for u in T.root.leaves:
        remaining = all_colors - {u.color}            # colors to which no best match has yet been found
        current = u.parent                            # start with direct parent of each node
        while remaining and current:
            colors_here = set()
            for v in current.leaves:
                if v.color in remaining:              # best match found
                    colors_here.add(v.color)
            
            arc_colors[current].update(colors_here)
            remaining -= colors_here
            current = current.parent
    
    return arc_colors


def redundant_edges(T, subtree_colors, arc_colors):
    
    red_edges = []
    
    for u, v in T.inner_edges():
        
        # colors s in sigma( L(T(u) \ T(v)) )
        aux_set = set()
        
        for v2 in u.children:
            if v2 is not v:
                aux_set.update(subtree_colors[v2])
        
        if not arc_colors[v].intersection(aux_set):
            red_edges.append((u, v))
    
    return red_edges


# --------------------------------------------------------------------------
#                               LRT FROM BMG
# --------------------------------------------------------------------------

def lrt_from_colored_graph(G, mincut=False, weighted_mincut=False):
    
    L = {v for v in G.nodes()}
    R = informative_triples(G)
    
    build = Build(R, L, mincut=mincut, weighted_mincut=weighted_mincut)
    
    tree = build.build_tree()
    
    if not tree:
        return None
    else:
        # assign label and colors to the leaves
        tree.reconstruct_information_from_graph(G)
        
        return tree


def correct_bmg(bmg_original):
    """Build the LRT (using min cut in BUILD algorithm) and return its BMG."""
    
    subtrees = []
    for sg in (bmg_original.subgraph(c)
               for c in nx.weakly_connected_components(bmg_original)):
        tree = lrt_from_colored_graph(sg, mincut=True)
        if tree:
            subtrees.append(tree)
            
    if len(subtrees) == 0:
        return None
    elif len(subtrees) == 1:
        tree = subtrees[0]
    else:
        tree = PhyloTree(PhyloTreeNode(0))
        for subtree in subtrees:
            tree.root.add_child(subtree.root)
    
    return bmg_from_tree(tree)


# --------------------------------------------------------------------------
#                          LRT FROM 2-col. BMG
#                         (new characterization)
# --------------------------------------------------------------------------
            
class TwoColoredLRT:
    
    def __init__(self, digraph):
        
        if not isinstance(digraph, nx.DiGraph):
            raise TypeError('not a digraph')
            
        self.digraph = digraph
        self.color_dict = sort_by_colors(digraph)
                
    
    def build_tree(self):
        
        if not is_properly_colored(self.digraph):
            raise RuntimeError('not a properly colored digraph')
        if len(self.color_dict) > 2:
            raise RuntimeError('more than 2 colors')
        
        # star tree if there is only one color
        if len(self.color_dict) == 1:
            root = PhyloTreeNode(-1)
            for v in self.digraph.nodes():
                root.add_child(
                    PhyloTreeNode(-1, label=self.digraph.nodes[v]['label'],
                                      color=self.digraph.nodes[v]['color']))
        # 2 colors
        else:
            roots = []
            for wcc in nx.weakly_connected_components(self.digraph):
                if len(wcc) == 1:
                    return False
                
                subroot = self._build_tree(self.digraph.subgraph(wcc).copy())
                
                if not subroot:
                    return False
                else:
                    roots.append(subroot)
            
            if len(roots) == 1:
                root = roots[0]
            else:
                root = PhyloTreeNode(-1)
                for subroot in roots:
                    root.add_child(subroot)
        
        tree = PhyloTree(root)
        tree.reconstruct_IDs()
        return tree
    
        
    def _build_tree(self, G):
            
        color_count = {color: 0 for color in self.color_dict.keys()}
        for v in G.nodes():
            color_count[G.nodes[v]['color']] += 1
        other_color = {color: G.order() - count
                       for color, count in color_count.items()}
        
        umbrella = {v for v in G.nodes() if 
                    other_color[G.nodes[v]['color']] == G.out_degree(v)}
        S_1 = {v for v in umbrella if umbrella.issuperset(G.predecessors(v))}
        S_2 = {v for v in S_1 if S_1.issuperset(G.predecessors(v))}
        
        if not S_2 or len(S_1) != len(S_2):
            return False
            
        node = PhyloTreeNode(-1)
        for v in S_2:
            node.add_child(PhyloTreeNode(v, label=G.nodes[v]['label'],
                                            color=G.nodes[v]['color']))
            G.remove_node(v)
        
        for wcc in nx.weakly_connected_components(G):
            
            if len(wcc) == 1:
                return False
            
            child = self._build_tree(G.subgraph(wcc).copy())
            
            if not child:
                return False
            else:
                node.add_child(child)
                
        return node

        
        
if __name__ == '__main__':
    
    import time
    
    N = 100
    
    T = PhyloTree.random_colored_tree(N, 2)
    print('--- T ---\n', T.to_newick())
    
    bmg = bmg_from_tree(T)
    
    start_time1 = time.time()
    # lrt_constr = LRTConstructor(bmg, mincut=False)
    # lrt1 = lrt_constr.build_tree()
    lrt1 = lrt_from_colored_graph(bmg, mincut=False)
    end_time1 = time.time()
    
    lrt2 = lrt_from_observable_tree(T)
    
    print('--- LRT1 ---\n', lrt1.to_newick())
    print('--- LRT2 ---\n', lrt2.to_newick())
    print('LRTs equal: {}'.format( lrt1.compare_topology(lrt2) ))
    
    bmg = bmg_from_tree(T)
    
    start_time2 = time.time()
    tc = TwoColoredLRT(bmg)
    lrt3 = tc.build_tree()
    end_time2 = time.time()
    
    lrt4 = lrt_from_observable_tree(T)
    print('--- LRT3 ---\n', lrt3.to_newick())
    print('--- LRT4 ---\n', lrt4.to_newick())
    print('LRTs equal: {}'.format( lrt3.compare_topology(lrt4) ))
    print(end_time1 - start_time1, end_time2 - start_time2)