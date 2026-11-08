from reasoning.lead.implementations import v1_basic as baseline, v2_causal_guided as causal_guided, v2_joint_route_planner as joint_route_planner


class Runtime:
    def __init__(self):
        self.gaps={'o':{'id':'o','kind':'operational','status':'open'},
                   'c':{'id':'c','kind':'causal','status':'open'},
                   'c2':{'id':'c2','kind':'causal','status':'open'},
                   'c3':{'id':'c3','kind':'causal','status':'open'}}
        self.attempts=[]; self.discoveries=[]; self.hypotheses={}


def public():
    return {'routes':[{'id':'maintenance','description':'Available equipment service records'}],
            'gaps':[{'id':'o','kind':'operational','status':'open','question':'How does machine work?',
                     'routes_to_consider':[{'route':'maintenance'}]},
                    *[{'id':gid,'kind':'causal','status':'open','question':f'What caused accident factor {gid}?',
                       'routes_to_consider':[{'route':'security'}]} for gid in ('c','c2','c3')]],
            'hypotheses':[],'graph_frontier':{}}


def action(gid,route,mode,direct=1):
    return {'gap_id':gid,'route':route,'mode':mode,'directness':direct,'burden':1,
            'question':'Please obtain evidence about the accident factor',
            'information_needed':'Time-scoped observations of equipment or aisle',
            'possible_effect':'Discriminate between competing causes of the accident'}


def test_joint_planner_values_future_shared_route_while_causal_prefers_immediate():
    r=Runtime();p=public()
    choices=[action('o','maintenance','request',direct=2),action('c','security','discover',direct=1)]
    assert baseline.rank(r,choices,p)[0]['action']==choices[0]
    assert causal_guided.rank(r,choices,p)[0]['action']==choices[0]
    selected=joint_route_planner.rank(r,choices,p)[0]
    assert selected['action']==choices[1]
    assert selected['breakdown']['open_needs_accessible_via_route']==3
    assert selected['breakdown']['route_access']>2
    assert selected['breakdown']['score_type']=='ordinal_heuristic_not_expected_information_gain'


def test_unknown_custodian_cannot_be_requested_before_discovery():
    r=Runtime();p=public()
    assert joint_route_planner.rank(r,[action('c','security','request')],p)==[]
    assert joint_route_planner.rank(r,[action('c','security','discover')],p)


def test_exhausted_gap_route_is_not_reissued():
    r=Runtime();r.attempts=[{'mode':'request','gap_id':'o','route':'maintenance'}]
    assert joint_route_planner.rank(r,[action('o','maintenance','request')],public())==[]
