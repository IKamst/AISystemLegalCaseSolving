function makeReduceOrFallback(callback, fallback) {
	return function() {
		return this.length > 0
			? this.reduce((a, b) => callback(a, b))
			: fallback;
	};
}

Array.prototype.max = makeReduceOrFallback(Math.max, 0);

Array.prototype.min = makeReduceOrFallback(Math.min, 0);

Array.prototype.sum = makeReduceOrFallback((a, b) => a + b, 0);

Array.prototype.flatten = makeReduceOrFallback((acc, arr) => acc.concat(arr), []);

if (!('includes' in Array.prototype)) {
    Array.prototype.includes = function(value) {
        return this.indexOf(value) !== -1;
    };
}