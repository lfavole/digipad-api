self.addEventListener("install", evt => {
	async function init() {
		console.log("Opening cache");
		await caches.open("cache");
	}
	evt.waitUntil(init());
});

self.addEventListener("fetch", async evt => {
	async function getFromCache(request) {
		ret = await caches.match(request);
		console.log(`Fetching ${request.url} from cache${ret ? "" : ", does not exist"}`);
		return ret;
	}
	async function fetchAndCache(request) {
		var response = await fetch(request);

		if(response.url.startsWith(location.origin + "/"))
			return response;

		var clonedResponse = response.clone();

		evt.waitUntil(
			caches.open("cache")
			.then(cache => {
				console.log(`Storing ${response.url || request.url + " <opaque response>"}`);
				return cache.put(request, clonedResponse);
			})
			.catch(console.error)
		);

		return response;
	}
	async function getResponse(evt) {
		var request = evt.request;
		var cachedResponse = await getFromCache(request);
		if(cachedResponse) {
			fetchAndCache(request).catch(console.error);
			return cachedResponse;
		}
		return await fetchAndCache(request);
	}
	evt.respondWith(getResponse(evt));
});
