/**
 * GitHub Actions 触发代理
 *
 * 部署方式：
 *   1. 登录 https://dash.cloudflare.com → Workers & Pages → Create Worker
 *   2. 粘贴本文件内容并部署
 *   3. Settings → Variables and Secrets → 添加：
 *      - GITHUB_PAT: GitHub Personal Access Token (需要 repo + workflow 权限)
 *      - GITHUB_REPO: ArthurUker/wuhan-teacher-job-tracker
 *   4. 复制 Worker URL（如 https://xxx.workers.dev），填入前端 TRIGGER_WORKER_URL
 */

const CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
};

export default {
    async fetch(request, env) {
        // CORS preflight
        if (request.method === 'OPTIONS') {
            return new Response(null, { headers: CORS_HEADERS });
        }

        // 只接受 POST
        if (request.method !== 'POST') {
            return json({ error: 'Method not allowed' }, 405);
        }

        try {
            const token = env.GITHUB_PAT;
            const repo = env.GITHUB_REPO || 'ArthurUker/wuhan-teacher-job-tracker';

            if (!token) {
                return json({ error: 'Server not configured' }, 500);
            }

            const [owner, repoName] = repo.split('/');

            // 1. 查找 crawl.yml 的 workflow ID
            const wfResp = await fetch(
                `https://api.github.com/repos/${owner}/${repoName}/actions/workflows`,
                { headers: githubHeaders(token) }
            );
            const { workflows } = await wfResp.json();
            const crawlWf = workflows?.find(w =>
                w.path === '.github/workflows/crawl.yml'
            );

            if (!crawlWf) {
                return json({ error: 'crawl.yml not found' }, 404);
            }

            // 2. 触发 workflow_dispatch
            const dispatchResp = await fetch(
                `https://api.github.com/repos/${owner}/${repoName}/actions/workflows/${crawlWf.id}/dispatches`,
                {
                    method: 'POST',
                    headers: { ...githubHeaders(token), 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ref: 'main' }),
                }
            );

            if (dispatchResp.status === 204) {
                return json({
                    success: true,
                    message: '爬虫已触发，约 2-3 分钟后数据将自动刷新',
                    runUrl: `https://github.com/${owner}/${repoName}/actions`,
                });
            }

            return json({
                error: `Trigger failed (${dispatchResp.status})`,
                detail: (await dispatchResp.text()).slice(0, 200),
            }, dispatchResp.status);

        } catch (err) {
            return json({ error: err.message }, 500);
        }
    },
};

function json(data, status = 200) {
    return new Response(JSON.stringify(data), {
        status,
        headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
    });
}

function githubHeaders(token) {
    return {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'CrawlTriggerProxy/1.0',
    };
}
