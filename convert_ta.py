import TSV
import sys
import sv
from sv import Breakpoint, BreakpointPair, Interval
import svmerge
from constants import ORIENT

TSV._verbose = True

header, rows = TSV.read_file(
        '/projects/POG/POG_data/POG098/wgs/GV2/POG098_POG098-OCT-1-unique-14-filters/POG098-OCT-1_genome_fusions_concat.tsv',
        retain = ['id'],
        split = {
            'breakpoint': ('^([^:]+):(\d+)\|([^:]+):(\d+)$', ['chr1', 'pos1', 'chr2', 'pos2']),
            'orientations': ('^([RL]),([RL])$', ['or1', 'or2']),
            'strands': ('^([\+-]),([\+-])$', ['strand1', 'strand2'])
            },
        cast = {'pos1': 'int', 'pos2': 'int'},
        strict = False
        )

UNC = 10
print('loaded', len(rows), 'rows')
breakpoints = []
for row in rows:
    b1 = Breakpoint(row['chr1'], row['pos1'] - UNC, row['pos1'] + UNC, row['or1'], row['strand1'], label=row['id'])
    b2 = Breakpoint(row['chr2'], row['pos2'] - UNC, row['pos2'] + UNC, row['or2'], row['strand2'], label=row['id'])
    breakpoints.append(BreakpointPair(b1, b2))
print()
clusters = sv.cluster_breakpoints(breakpoints, r=20, k=15)

more_breakpoints = svmerge.load_input_file('delly_svmerge.tsv')

print('loaded', len(breakpoints), 'breakpoints from TA and', len(more_breakpoints), 'from delly')

more_clusters = sv.cluster_breakpoints(breakpoints + more_breakpoints, r=20, k=15)

print('initially found', len(clusters), 'clusters. with delly found', len(more_clusters), 'clusters')

high_supported_clusters = sum([1 for k, c in more_clusters.items() if len(c) > 1])
print('found', high_supported_clusters, 'high_supported_clusters')
print()
with open('result.tsv', 'w') as fh:
    fh.write('type\tcentroid_breakpoint_pair\tunion\tintersection\tsupport\tstart_dist\t_end_dist\tcumu_dist\toriginal_pairs\n')
    last_pair = None
    for pair, support in sorted(more_clusters.items(), key=lambda x: x[0].key):
        if len(support) <= 0:
            continue
        d1 = -1
        d2 = -1
        if last_pair is not None \
                and last_pair.break1.chr == pair.break1.chr \
                and last_pair.break2.chr == pair.break2.chr:
            d1 = abs(last_pair.break1.pos - pair.break1.pos)
            d2 = abs(last_pair.break2.pos - pair.break2.pos)
        event_type = '?'

        if ORIENT.NS in [pair.break1.orient, pair.break2.orient]:
            if pair.break1.chr != pair.break2.chr:
                event_type = 'translocation-?'
        else:
            if pair.break1.orient == pair.break2.orient:
                if pair.break1.chr != pair.break2.chr:
                    event_type = 'translocation-inversion'
                else:
                    event_type = 'inversion'
            elif pair.break1.chr != pair.break2.chr:
                event_type = 'translocation'
            elif pair.break1.orient == ORIENT.RIGHT:
                event_type = 'duplication'
            else:
                event_type = 'deletion'
        u1 = Interval.union([s.break1 for s in support])
        u2 = Interval.union([s.break2 for s in support])
        i1 = Interval.intersection([s.break1 for s in support])
        i2 = Interval.intersection([s.break2 for s in support])
        
        fh.write( '{type}\t{pair}\t{u1}==>{u2}\t{i1}==>{i2}'.format(
            type=event_type, pair=pair, u1=len(u1) , u2=len(u2), i1=len(i1 if i1 is not None else []), i2=len(i2 if i2 is not None else [])) 
                +  '\t{3}\t{0}\t{1}\t{2}\t'.format(d1, d2, d1 + d2, len(support))
                + ';'.join([str(k) for k in support]) + '\n')
        last_pair = pair
