const { Client } = require('@notionhq/client');
const notion = new Client({
    auth: process.env.NOTION_TOKEN,
    notionVersion: '2025-09-03',
});
const DS_ID = process.env.NOTION_DATA_SOURCE_ID;

const PHASE_ORDER = ['기획', '설계', '개발', '검증', '배포', '운영'];

function parseBranch(ref) {
    const b = (ref || '').toLowerCase();
    let role = null;
    if (b.startsWith('fe/')) role = 'FE';
    else if (b.startsWith('be/')) role = 'BE';
    else if (b.startsWith('ai/')) role = 'AI';

    let phase = null;
    if (b === 'main') phase = '배포';
    else if (b.startsWith('release/')) phase = '검증';
    else if (b.startsWith('hotfix/') || b.startsWith('fix/')) phase = '운영';
    else if (/\/feat[-/]/.test(b) || b.startsWith('feat/')) phase = '개발';

    let priority = '낮음';
    if (b.startsWith('hotfix/')) priority = '높음';
    else if (b.startsWith('release/') || b.startsWith('fix/')) priority = '보통';

    return { role, phase, priority };
}

function determineStatus() {
    const event = process.env.EVENT_NAME;
    const ref = process.env.REF_NAME || '';
    const baseRef = process.env.BASE_REF || '';
    const prMerged = process.env.PR_MERGED === 'true';

    if (event === 'push' && (ref === 'main' || ref === 'develop')) return '완료';
    if (event === 'pull_request' && prMerged && (baseRef === 'main' || baseRef === 'develop')) return '완료';
    return '진행 중';
}

function extractTaskIds(texts) {
    const ids = new Set();
    const depends = new Set();
    let title = '';
    for (const text of texts) {
        if (!text) continue;

        const matches = [...text.matchAll(/\[([A-Z]+-\d+)\]/g)];
        matches.forEach((m) => ids.add(m[1]));

        const mergeMatch = text.match(/Merge (?:pull request #\d+ )?from [\w-]+\/([\w\-/]+)/);
        if (mergeMatch) {
            ids.add(mergeMatch[1].replace(/\//g, '-').toLowerCase());
        }

        const depMatch = text.match(/depends\s*:\s*([A-Z0-9,\-\s]+)/i);
        if (depMatch) {
            depMatch[1].split(',').map((s) => s.trim()).filter(Boolean).forEach((d) => depends.add(d));
        }
        if (!title && matches.length > 0) {
            title = text.replace(/\[[A-Z]+-\d+\]/g, '').replace(/depends\s*:.*$/im, '').split('\n')[0].trim();
        }
    }
    return { ids: [...ids], depends: [...depends], title };
}

async function findPage(taskId) {
    const r = await notion.dataSources.query({
        data_source_id: DS_ID,
        filter: { property: 'Task ID', rich_text: { equals: taskId } },
        page_size: 1,
    });
    return r.results[0] || null;
}

async function findOpenPRForBranch(branch) {
    const token = process.env.GITHUB_TOKEN;
    const repo = process.env.GITHUB_REPOSITORY;
    if (!token || !repo || !branch) return null;

    const owner = repo.split('/')[0];
    const url = `https://api.github.com/repos/${repo}/pulls?head=${owner}:${branch}&state=open`;
    try {
        const res = await fetch(url, {
            headers: {
                Authorization: `Bearer ${token}`,
                Accept: 'application/vnd.github+json',
                'X-GitHub-Api-Version': '2022-11-28',
            },
        });
        if (!res.ok) {
            console.log(`   ⚠ GitHub API ${res.status}: ${await res.text()}`);
            return null;
        }
        const prs = await res.json();
        return prs[0] || null;
    } catch (e) {
        console.log(`   ⚠ PR 조회 실패: ${e.message}`);
        return null;
    }
}

async function appendLink(pageId, { label, url, emoji }) {
    await notion.blocks.children.append({
        block_id: pageId,
        children: [
            {
                object: 'block',
                type: 'callout',
                callout: {
                    rich_text: [
                        { type: 'text', text: { content: `${label}\n` } },
                        { type: 'text', text: { content: url, link: { url } } },
                    ],
                    icon: { emoji: emoji || '🔗' },
                    color: 'gray_background',
                },
            },
        ],
    });
}

async function pageHasLink(pageId, url) {
    try {
        const blocks = await notion.blocks.children.list({ block_id: pageId, page_size: 100 });
        return blocks.results.some((b) => {
            if (b.type !== 'callout') return false;
            const texts = b.callout?.rich_text || [];
            return texts.some((t) => t.text?.link?.url === url || t.href === url);
        });
    } catch {
        return false;
    }
}

async function main() {
    if (!DS_ID) throw new Error('NOTION_DATA_SOURCE_ID 환경변수가 없습니다.');

    const event = process.env.EVENT_NAME;

    let texts = [];
    let prUrl = null;
    let prTitle = null;
    let commitUrl = null;
    let commitCount = 0;

    if (event === 'push') {
        const commits = JSON.parse(process.env.COMMITS_JSON || '[]');
        texts = commits.map((c) => c.message);
        commitCount = commits.length;
        commitUrl = process.env.COMPARE_URL || process.env.HEAD_COMMIT_URL || null;

        const pr = await findOpenPRForBranch(process.env.REF_NAME);
        if (pr) {
            prUrl = pr.html_url;
            prTitle = pr.title;
            console.log(`🔍 브랜치 ${process.env.REF_NAME}의 열린 PR 발견: #${pr.number}`);
        } else {
            console.log(`🔍 브랜치 ${process.env.REF_NAME}에 열린 PR 없음`);
        }
    } else if (event === 'pull_request') {
        texts = [process.env.PR_TITLE, process.env.PR_BODY];
        prUrl = process.env.PR_URL;
        prTitle = process.env.PR_TITLE;
    }

    let { ids: taskIds, depends, title } = extractTaskIds(texts);

    if (taskIds.length === 0) {
        const branch = event === 'pull_request' ? process.env.HEAD_REF : process.env.REF_NAME;
        if (!branch || branch === 'main' || branch === 'develop') {
            console.log('Task ID 없음 & 추적 대상 브랜치 아님, 스킵');
            return;
        }
        const autoId = branch.replace(/\//g, '-').toLowerCase();
        taskIds = [autoId];
        if (!title) {
            title = texts.find((t) => t && t.trim())?.split('\n')[0]?.trim() || branch;
        }
        console.log(`🏷  자동 Task ID: ${autoId}`);
    }

    const branch = event === 'pull_request' ? process.env.HEAD_REF : process.env.REF_NAME;
    const { role, phase, priority } = parseBranch(branch);
    const newPhaseIdx = phase ? PHASE_ORDER.indexOf(phase) : -1;
    const status = determineStatus();

    for (const taskId of taskIds) {
        const existing = await findPage(taskId);

        const relationIds = [];
        for (const dep of depends) {
            const p = await findPage(dep);
            if (p) relationIds.push({ id: p.id });
        }

        const props = {};
        if (role) props['역할'] = { select: { name: role } };
        if (priority) props['우선순위'] = { select: { name: priority } };
        if (relationIds.length > 0) props['선행 작업'] = { relation: relationIds };
        props['상태'] = { status: { name: status } };

        if (phase) {
            const curPhase = existing?.properties['작업 구분']?.select?.name;
            const curIdx = curPhase ? PHASE_ORDER.indexOf(curPhase) : -1;
            const shouldAdvance = phase === '운영' || newPhaseIdx >= curIdx;
            if (shouldAdvance) props['작업 구분'] = { select: { name: phase } };
        }

        let pageId;
        if (existing) {
            await notion.pages.update({ page_id: existing.id, properties: props });
            pageId = existing.id;
            console.log(`🔄 ${taskId} 갱신 (상태=${status}, 단계=${phase || '유지'})`);
        } else {
            props['작업 이름'] = { title: [{ text: { content: title || taskId } }] };
            props['Task ID'] = { rich_text: [{ text: { content: taskId } }] };
            props['작업일'] = { date: { start: new Date().toISOString().slice(0, 10) } };
            if (!props['작업 구분']) props['작업 구분'] = { select: { name: '개발' } };

            const page = await notion.pages.create({
                parent: { type: 'data_source_id', data_source_id: DS_ID },
                properties: props,
            });
            pageId = page.id;
            console.log(`✨ ${taskId} 생성 (상태=${status})`);
        }

        // PR 링크
        if (prUrl) {
            if (!(await pageHasLink(pageId, prUrl))) {
                await appendLink(pageId, {
                    label: `PR: ${prTitle || ''}`,
                    url: prUrl,
                    emoji: '🔀',
                });
                console.log(`   📎 PR 링크 첨부`);
            }
        }

        // 커밋 변경점 링크 (push 이벤트)
        if (event === 'push' && commitUrl) {
            if (!(await pageHasLink(pageId, commitUrl))) {
                const label = commitCount > 1 ? `커밋 ${commitCount}개 변경점` : '커밋 변경점';
                await appendLink(pageId, {
                    label,
                    url: commitUrl,
                    emoji: '📝',
                });
                console.log(`   📝 커밋 링크 첨부: ${commitUrl}`);
            }
        }
    }
}

main().catch((e) => { console.error(e); process.exit(1); });