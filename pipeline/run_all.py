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

STEPS = ['make_eps', 'run_chain', 'run_entry', 'run_dyn', 'run_sens2', 'analyze_v3', 'analyze_v3b',
         'build_web2', 'build_site', 'build_dash']
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
    keep = REPO / 'data' / 'reasons.json'
    saved = keep.read_bytes() if keep.exists() else b'[]'
    for sub in ('data', 'px'):
        shutil.rmtree(REPO / sub, ignore_errors=True)
        shutil.copytree(web / sub, REPO / sub)
    keep.write_bytes(saved)
    import json as _j
    (REPO / 'data' / 'updated.json').write_text(_j.dumps({'t': time.strftime('%Y-%m-%d %H:%M'), 'd': last_date()}), encoding='utf-8')
    log('웹 파일 복사 완료 ->', REPO)


def git(*a):
    return subprocess.run(['git', '-C', str(REPO), *a], capture_output=True, text=True, encoding='utf-8', errors='replace')


def pull():
    """GitHub 웹에서 고친 내용(pipeline/ 코드, 화면)을 먼저 받아옵니다."""
    if (REPO / '.git').exists():
        r = git('pull', '--rebase', '--autostash')
        log('GitHub에서 최신 코드 받기', '완료' if r.returncode == 0 else '실패: ' + (r.stderr or r.stdout)[-300:])


def push():
    if not (REPO / '.git').exists():
        log('저장소 폴더가 git 저장소가 아니라 업로드를 건너뜁니다.')
        return
    git('pull', '--rebase', '--autostash')
    git('add', '-A', 'index.html', '.nojekyll', 'data', 'px', 'pipeline')
    r = git('commit', '-m', f'daily update {last_date()}')
    if 'nothing to commit' in (r.stdout + r.stderr):
        log('바뀐 내용이 없어 업로드하지 않았습니다.')
        return
    r = git('push')
    log('GitHub 업로드', '성공' if r.returncode == 0 else '실패: ' + (r.stderr or r.stdout)[-400:])


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
    args = set(sys.argv[1:])
    log('===== 작업 시작 =====')
    if '--no-push' not in args:
        step('코드 받기', pull)
    kiwoom_ok = False
    if '--no-kiwoom' not in args:
        import update_daily
        kiwoom_ok = step('키움 일봉', update_daily.main)
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
    log('===== 작업 끝 =====')
    return 0


if __name__ == '__main__':
    sys.exit(main())
