/**
 * GitHub Actions 触发代理 + 状态查询
 *
 * 部署方式（Git 集成）：
 *   1. 在 Cloudflare Dashboard 创建 Git 集成 Worker
 *   2. Root directory 设为 `workers`
 *   3. Settings → Variables and Secrets → 添加：
 *      - GITHUB_PAT (Secret): GitHub Personal Access Token (需要 repo + workflow 权限)
 *      - GITHUB_REPO (Variable): ArthurUker/wuhan-teacher-job-tracker
 *      - AUTH_TOKEN (Secret): 用于鉴权的 Token（可选，但强烈建议配置）
 *
 * 接口说明：
 *   POST / → 触发爬虫（返回 runId）
 *   GET  / → 查询最新一次 workflow run 的状态
 */

const CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
};

export default {
    async fetch(request, env) {
        // CORS preflight
        if (request.method === 'OPTIONS') {
            return new Response(null, { headers: CORS_HEADERS });
        }

        // 鉴权检查（如果配置了 AUTH_TOKEN）
        if (env.AUTH_TOKEN) {
            const authHeader = request.headers.get('Authorization');
            if (!authHeader || authHeader !== `Bearer ${env.AUTH_TOKEN}`) {
                return json({ error: 'Unauthorized' }, 401);
            }
        }

        if (request.method === 'POST') {
            return await triggerCrawl(env);
        }

        if (request.method === 'GET') {
            return await checkStatus(env);
        }

        return json({ error: 'Method not allowed' }, 405);
    },
};

/** POST：触发 GitHub Actions 爬虫 */
async function triggerCrawl(env) {
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

        if (!wfResp.ok) {
            const errorText = await wfResp.text();
            return json({
                error: 'Failed to fetch workflows',
                status: wfResp.status,
                detail: errorText.slice(0, 200),
            }, wfResp.status);
        }

        const wfData = await wfResp.json();

        if (!wfData.workflows || !Array.isArray(wfData.workflows)) {
            return json({ error: 'Invalid workflow response' }, 500);
        }

        const crawlWf = wfData.workflows.find(w =>
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

        if (dispatchResp.status !== 204) {
            const errorDetail = await dispatchResp.text();
            return json({
                error: `Trigger failed (${dispatchResp.status})`,
                detail: errorDetail.slice(0, 200),
            }, dispatchResp.status);
        }

        // 3. 获取刚触发的 run ID（等待 2 秒让 GitHub 创建 run）
        let runId = null;
        try {
            await new Promise(resolve => setTimeout(resolve, 2000));
            const runsResp = await fetch(
                `https://api.github.com/repos/${owner}/${repoName}/actions/workflows/${crawlWf.id}/runs?per_page=1`,
                { headers: githubHeaders(token) }
            );
            if (runsResp.ok) {
                const runsData = await runsResp.json();
                if (runsData.workflow_runs && runsData.workflow_runs.length > 0) {
                    runId = runsData.workflow_runs[0].id;
                }
            }
        } catch (e) {
            // 忽略获取 run ID 失败，不影响触发结果
        }

        return json({
            success: true,
            message: '爬虫已触发，约 2-5 分钟后数据将自动刷新',
            runUrl: `https://github.com/${owner}/${repoName}/actions`,
            runId: runId,
        });

    } catch (err) {
        return json({ error: err.message }, 500);
    }
}

/** GET：查询最新 workflow run 的状态 */
async function checkStatus(env) {
    try {
        const token = env.GITHUB_PAT;
        const repo = env.GITHUB_REPO || 'ArthurUker/wuhan-teacher-job-tracker';

        if (!token) {
            return json({ error: 'Server not configured' }, 500);
        }

        const [owner, repoName] = repo.split('/');

        // 获取最新的 workflow run
        const runsResp = await fetch(
            `https://api.github.com/repos/${owner}/${repoName}/actions/runs?per_page=1`,
            { headers: githubHeaders(token) }
        );

        if (!runsResp.ok) {
            return json({ error: 'Failed to fetch runs' }, runsResp.status);
        }

        const runsData = await runsResp.json();

        if (!runsData.workflow_runs || runsData.workflow_runs.length === 0) {
            return json({ status: 'not_found' });
        }

        const latestRun = runsData.workflow_runs[0];

        return json({
            status: latestRun.status,         // queued / in_progress / completed
            conclusion: latestRun.conclusion,  // success / failure / cancelled / null
            runId: latestRun.id,
            htmlUrl: latestRun.html_url,
            createdAt: latestRun.created_at,
            updatedAt: latestRun.updated_at,
        });

    } catch (err) {
        return json({ error: err.message }, 500);
    }
}

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
