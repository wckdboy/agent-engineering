// Keep the existing worker identity so old deployments and URLs remain manageable.
const aliases = new Set(['adamant.cc', 'www.adamant.cc', 'www.creed.sh']);

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (aliases.has(url.hostname)) {
      url.protocol = 'https:';
      url.host = 'creed.sh';
      return Response.redirect(url.href, 308);
    }
    return env.ASSETS.fetch(request);
  },
};
