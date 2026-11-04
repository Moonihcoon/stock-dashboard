"""1단계: 급등 에피소드 찾기 (기준 조건 +80% / 3천억 3일)."""
import pickle, sys
sys.path.insert(0, '.')
from analyze_v2 import *
from common import analysis_panel
eps = find_episodes(analysis_panel(), P())
pickle.dump(eps, open('eps_v2.pkl', 'wb'))
print('에피소드', len(eps))
