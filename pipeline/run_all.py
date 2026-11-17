"""매일 한 번 실행하는 전체 작업.

1) 키움 일봉 업데이트  2) 통계 분석 1~9번 재계산  3) 분봉 수집(급등 종목)
4) 상승 이유 수집(네이버)  5) 대시보드 파일 생성  6) GitHub 업로드

python run_all.py              전체
python run_all.py --no-kiwoom  키움 수신 없이 재계산·업로드만
python run_all.py --no-push    업로드 안 함
"""
from __future__ import annotations
import os, runpy, shutil, subprocess, sys, time, traceback
from pathlib import Path

PIPE = Path(__file__).resolve().parent
sys.path[:0] = [str(PIPE), str(PIPE / 'analysis')]
from common import REPO, work_dir, log, opt, load_panel, last_date  # noqa: E402

STEPS = ['make_eps', 'run_chain', 'run_entry', 'run_dyn', 'run_sens2', 'analyze_v3', 'analyze_v3b', 'analyze_v4',
         'build_web2', 'build_site', 'build_dash', 'build_top']
HEAD = ('<!doctype html>\n<html lang="ko">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<style>html,body{margin:0}</style>\n')


def analysis():
    w = work_dir()
    web = w / 'web'
    for sub in ('data', 'px'):
        (web / sub).mkdir(parents=True, exist_ok=True)
    for f in (PIPE / 'web_src').iterdir():
        shutil.copy(f, web / f.name)
    cwd = os.getcwd(); os.chdir(w)
    try:
        for s in STEPS:
            t0 = time.time()
            log(f'[분석] {s} 시작')
            runpy.run_path(str(PIPE / 'analysis' / f'{s}.py'), run_name='__main__')
            log(f'[분석] {s} 완료 {time.time() - t0:.0f}초')
    finally:
        os.chdir(cwd)


def publish():
    web = work_dir() / 'web'
    page = (web / 'index.html').read_text(encoding='utf-8')
    if not page.lstrip().lower().startswith('<!doctype'):
        page = HEAD + page
    (REPO / 'index.html').write_text(page, encoding='utf-8')
    (REPO / '.nojekyll').write_text('', encoding='utf-8')
    keeps = {n: (REPO / 'data' / n).read_bytes() for n in ('reasons.json', 'themes.json') if (REPO / 'data' / n).exists()}
    for sub in ('data', 'px'):
        shutil.rmtree(REPO / sub, ignore_errors=True)
        shutil.copytree(web / sub, REPO / sub)
    for n, b in keeps.items():
        (REPO / 'data' / n).write_bytes(b)
    if 'reasons.json' not in keeps:
        (REPO / 'data' / 'reasons.json').write_text('[]', encoding='utf-8')
    import json as _j
    (REPO / 'data' / 'updated.json').write_text(_j.dumps({'t': time.strftime('%Y-%m-%d %H:%M'), 'd': last_date()}), encoding='utf-8')
    log('웹 파일 복사 완료 ->', REPO)


def git(*a):
    return subprocess.run(['git', '-C', str(REPO), *a], capture_output=True, text=True, encoding='utf-8', errors='replace')


def migrate_remote():
    """GitHub 저장소를 my-bank 로 옮긴 뒤, 아직 옛 저장소를 쓰고 있는 PC를 자동으로 my-bank 로 바꿉니다.
    my-bank 에 대시보드 파일(pipeline/run_all.py)이 올라와 있을 때만 바꿉니다(안 올라와 있으면 옛 저장소 유지)."""
    if not (REPO / '.git').exists():
        return
    o = git('remote', 'get-url', 'origin').stdout.strip()
    if not o or 'my-bank' in o.lower() or '/' not in o:
        return
    new = o.rsplit('/', 1)[0] + '/my-bank.git'
    r = git('fetch', new, 'main')
    if r.returncode != 0:
        return
    if git('cat-file', '-e', 'FETCH_HEAD:pipeline/run_all.py').returncode != 0:
        log('my-bank 에 아직 대시보드 파일이 없어 옛 저장소를 계속 씁니다.')
        return
    r = git('remote', 'set-url', 'origin', new)
    log('GitHub 저장소를 my-bank 로 바꿨습니다.' if r.returncode == 0 else '저장소 주소 변경 실패: ' + (r.stderr or r.stdout)[-200:])


def pull():
    """GitHub의 최신 상태(다른 PC가 올린 결과, GitHub 웹에서 고친 코드)로 맞춥니다.
    이 PC의 웹 파일은 매번 새로 만들기 때문에 로컬 변경은 버려도 됩니다."""
    if not (REPO / '.git').exists():
        return
    r = git('fetch', 'origin')
    if r.returncode != 0:
        log('GitHub 받기 실패(인터넷 확인): ' + (r.stderr or r.stdout)[-300:])
        return
    r = git('reset', '--hard', 'origin/main')
    log('GitHub에서 최신 코드 받기', '완료' if r.returncode == 0 else '실패: ' + (r.stderr or r.stdout)[-300:])


def push():
    if not (REPO / '.git').exists():
        log('저장소 폴더가 git 저장소가 아니라 업로드를 건너뜁니다.')
        return
    for attempt in range(3):
        git('fetch', 'origin')
        git('reset', '--mixed', 'origin/main')      # 방금 만든 파일은 그대로 두고 기준만 최신으로
        git('add', '-A', 'index.html', '.nojekyll', 'data', 'px', 'pipeline')
        r = git('commit', '-m', f'daily update {last_date()}')
        if 'nothing to commit' in (r.stdout + r.stderr):
            log('바뀐 내용이 없어 업로드하지 않았습니다.')
            return
        r = git('push')
        if r.returncode == 0:
            log('GitHub 업로드 성공')
            return
        time.sleep(10)
    log('GitHub 업로드 실패: ' + (r.stderr or r.stdout)[-400:])


def share_dir():
    """공유용 저장소(상승률 200) 로컬 폴더. 설정 [share] dir, 없으면 저장소 옆 K23934959 폴더."""
    d = opt('share', 'dir', '')
    return Path(d) if d else REPO.parent / 'K23934959'


def publish_share():
    """'상승률 200' 페이지와 거기에 필요한 파일만 공유용 저장소에 올립니다(통계·후보종목 데이터는 올리지 않음)."""
    sd = share_dir()
    page = work_dir() / 'web' / 'rank.html'
    if not page.exists():
        log('rank.html 이 없어 공유 페이지 업로드를 건너뜁니다.')
        return
    if not (sd / '.git').exists():
        # 이 PC에 공유용 저장소 복제본이 없으면 메인 저장소와 같은 계정의 K23934959 를 받아 옵니다.
        o = git('remote', 'get-url', 'origin').stdout.strip()
        url = opt('share', 'url', '') or (o.rsplit('/', 1)[0] + '/K23934959.git' if '/' in o else '')
        r = subprocess.run(['git', 'clone', url, str(sd)], capture_output=True, text=True, encoding='utf-8', errors='replace') if url else None
        if r is None or r.returncode != 0 or not (sd / '.git').exists():
            log('공유용 저장소(K23934959)를 받지 못해 공유 페이지 업로드를 건너뜁니다. GitHub에 저장소를 만들었는지 확인하세요. ' + ((r.stderr or r.stdout)[-200:] if r else ''))
            return
        log('공유용 저장소를 이 PC에 받았습니다: ' + str(sd))
    def g(*a):
        return subprocess.run(['git', '-C', str(sd), *a], capture_output=True, text=True, encoding='utf-8', errors='replace')
    g('fetch', 'origin')
    g('checkout', '-B', 'main')
    if g('rev-parse', '--verify', 'origin/main').returncode == 0:
        g('reset', '--hard', 'origin/main')
    tp = page.read_text(encoding='utf-8')
    if not tp.lstrip().lower().startswith('<!doctype'):
        tp = HEAD + tp
    (sd / 'index.html').write_text(tp, encoding='utf-8')
    (sd / '.nojekyll').write_text('', encoding='utf-8')
    for sub in ('data', 'px'):
        shutil.rmtree(sd / sub, ignore_errors=True)
    (sd / 'data').mkdir(parents=True, exist_ok=True)
    for n in ('dates.json', 'tick.json', 'spark.json', 'reasons.json', 'themes.json', 'updated.json'):
        if (REPO / 'data' / n).exists():
            shutil.copy(REPO / 'data' / n, sd / 'data' / n)
    shutil.copytree(REPO / 'data' / 'top', sd / 'data' / 'top')
    shutil.copytree(REPO / 'px' / 'm', sd / 'px' / 'm')
    for attempt in range(3):
        g('add', '-A', '.')
        r = g('commit', '-m', f'rank200 update {last_date()}')
        if 'nothing to commit' in (r.stdout + r.stderr):
            log('공유 페이지: 바뀐 내용이 없어 업로드하지 않았습니다.')
            return
        r = g('push', 'origin', 'HEAD:main')
        if r.returncode == 0:
            log('공유 페이지(상승률 200) 업로드 성공')
            return
        g('fetch', 'origin')
        g('reset', '--soft', 'origin/main')
        time.sleep(10)
    log('공유 페이지 업로드 실패: ' + (r.stderr or r.stdout)[-400:])


def already_done():
    """자동 실행용: 오늘(평일, 장 마감 후) 시세가 이미 올라가 있으면 True."""
    import json, datetime
    try:
        u = json.load(open(REPO / 'data' / 'updated.json', encoding='utf-8'))
    except (OSError, ValueError):
        return False
    now = datetime.datetime.now()
    if now.weekday() >= 5 or now.hour * 60 + now.minute < 15 * 60 + 40:
        return False
    return u.get('d') == now.strftime('%Y-%m-%d')


def step(name, fn):
    try:
        fn()
        return True
    except SystemExit as e:
        log(f'{name} 중단: {e}')
    except Exception as e:
        log(f'{name} 오류: {type(e).__name__}: {e}')
        log('  (자세한 내용) ' + traceback.format_exc()[-1200:].replace(chr(10), chr(10) + '  '))
    return False


def main():
    lock = work_dir() / 'running.lock'
    lock.write_text(time.strftime('%Y-%m-%d %H:%M'))
    try:
        return _main()
    finally:
        try:
            lock.unlink()
        except OSError:
            pass


def _main():
    args = set(sys.argv[1:])
    log('===== 작업 시작 =====')
    if '--no-push' not in args:
        step('저장소 이전 확인', migrate_remote)
        step('코드 받기', pull)
    if '--auto' in args and already_done():
        log('오늘 업데이트는 이미 GitHub에 올라가 있어 건너뜁니다(다른 PC가 먼저 실행).')
        return 0
    kiwoom_ok = False
    if '--no-kiwoom' not in args:
        import update_daily
        kiwoom_ok = step('키움 일봉', update_daily.main)
    import minute_daily
    step('분봉 일별 요약', minute_daily.main)
    load_panel(refresh=True)
    if not step('통계 분석', analysis):
        log('분석이 실패해서 웹 파일은 바꾸지 않았습니다.')
        return 1
    if kiwoom_ok:
        import update_minute
        step('분봉', update_minute.main)
    publish()
    import reasons_dart
    step('상승 이유', reasons_dart.main)
    if '--no-push' not in args and opt('options', 'push', 'yes').lower() in ('yes', 'y', '1', 'true'):
        step('업로드', push)
        step('공유 페이지', publish_share)
    log('===== 작업 끝 =====')
    return 0


if __name__ == '__main__':
    sys.exit(main())
