// Downloads retain the original; phones and unsupported decoders use a cached SDR playback copy.
export function compatibleVideoUrl(src,base=globalThis.location?.href??'http://localhost/') {
  const url=new URL(src,base);
  if(url.origin!==new URL(base).origin||!url.pathname.endsWith('/view')
    ||url.searchParams.get('type')!=='output'||!url.searchParams.get('subfolder')?.startsWith('h3_sequences/')
    ||!url.searchParams.get('filename')?.toLowerCase().endsWith('.mp4'))return null;
  url.pathname=url.pathname.slice(0,-5)+'/h3c/video/preview';
  return url.href;
}

export function videoPlaybackUrl(src,mobile=!!globalThis.navigator?.userAgentData?.mobile
  ||/Android|iPhone|iPad|iPod/.test(globalThis.navigator?.userAgent??''),base) {
  return mobile?compatibleVideoUrl(src,base)??src:src;
}
