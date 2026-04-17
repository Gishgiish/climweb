/**
 * Hero Forecast Widget Loader
 *
 * This script loads the weather forecast widget data into the hero banner.
 * It fetches data from the home-weather-widget endpoint and replaces
 * the skeleton with the actual forecast content.
 */
(function() {
    'use strict';

    document.addEventListener('DOMContentLoaded', function() {
        var widgetWrapper = document.getElementById('weather-widget-wrapper');
        if (!widgetWrapper) return;

        // Get the widget URL from data attribute or use default
        var widgetUrl = widgetWrapper.getAttribute('data-widget-url');
        if (!widgetUrl) {
            // Try to get from window variable if available
            if (window.homeWeatherWidgetUrl) {
                widgetUrl = window.homeWeatherWidgetUrl;
            } else {
                console.warn('Hero forecast widget: No widget URL configured');
                return;
            }
        }

        // Show loader
        var loader = widgetWrapper.querySelector('.loader-wrapper');
        if (loader) {
            loader.classList.add('is-active');
        }

        // Fetch the widget content
        fetch(widgetUrl)
            .then(function(response) {
                if (!response.ok) {
                    throw new Error('Failed to load forecast widget');
                }
                return response.text();
            })
            .then(function(html) {
                // Check if we got actual content or empty response
                if (html && html.trim().length > 0) {
                    // Replace skeleton with actual content
                    widgetWrapper.innerHTML = html;
                    
                    // Initialize the glide slider if present
                    if (document.getElementById('single-forecast-slider')) {
                        initializeGlideSlider();
                    }
                    
                    // Initialize city search if present
                    initializeCitySearch();
                } else {
                    // Empty response - no cities configured
                    showNoDataMessage(widgetWrapper);
                }
            })
            .catch(function(error) {
                console.error('Hero forecast widget error:', error);
                showNoDataMessage(widgetWrapper);
            });
    });
    
    function showNoDataMessage(widgetWrapper) {
        widgetWrapper.innerHTML = '<div class="forecast-no-data" style="color:#fff;padding:30px;text-align:center;">' +
            '<p style="font-size:16px;margin-bottom:10px;">Weather forecast data is not configured</p>' +
            '<p style="font-size:13px;opacity:0.7;">Please configure cities and forecast data in the Wagtail admin.</p>' +
            '</div>';
    }

    /**
     * Initialize the Glide slider for forecast display
     */
    function initializeGlideSlider() {
        if (typeof Glide === 'undefined') {
            console.warn('Glide.js not loaded');
            return;
        }

        var sliderEl = document.getElementById('single-forecast-slider');
        if (sliderEl) {
            new Glide('#single-forecast-slider', {
                type: 'carousel',
                perView: 3,
                gap: 10,
                breakpoints: {
                    768: {
                        perView: 1
                    },
                    1024: {
                        perView: 2
                    }
                }
            }).mount();
        }
    }

    /**
     * Initialize city search functionality
     */
    function initializeCitySearch() {
        var searchInput = document.getElementById('city-search');
        var searchMenu = document.getElementById('city-search-menu');
        
        if (!searchInput || !searchMenu) return;

        var searchUrl = searchInput.getAttribute('data-search-url');
        if (!searchUrl && window.citySearchUrl) {
            searchUrl = window.citySearchUrl;
        }

        if (!searchUrl) return;

        var debounceTimer;
        searchInput.addEventListener('input', function() {
            clearTimeout(debounceTimer);
            var query = this.value.trim();
            
            if (query.length < 2) {
                searchMenu.innerHTML = '';
                searchMenu.parentElement.classList.remove('is-active');
                return;
            }

            debounceTimer = setTimeout(function() {
                fetch(searchUrl + '?q=' + encodeURIComponent(query))
                    .then(function(response) { return response.json(); })
                    .then(function(data) {
                        renderSearchResults(data);
                    })
                    .catch(function(err) {
                        console.error('City search error:', err);
                    });
            }, 300);
        });

        function renderSearchResults(cities) {
            if (!cities || cities.length === 0) {
                searchMenu.innerHTML = '<div class="dropdown-content"><p class="dropdown-item" style="padding:10px;">No locations found</p></div>';
                searchMenu.parentElement.classList.add('is-active');
                return;
            }

            var html = '<div class="dropdown-content">';
            cities.forEach(function(city) {
                html += '<a class="dropdown-item city-result" data-slug="' + city.slug + '" data-url="' + (city.url || '') + '">' +
                    city.name + '</a>';
            });
            html += '</div>';
            
            searchMenu.innerHTML = html;
            searchMenu.parentElement.classList.add('is-active');

            // Add click handlers
            searchMenu.querySelectorAll('.city-result').forEach(function(item) {
                item.addEventListener('click', function(e) {
                    e.preventDefault();
                    var slug = this.getAttribute('data-slug');
                    loadCityForecast(slug);
                    searchMenu.parentElement.classList.remove('is-active');
                    searchInput.value = this.textContent;
                });
            });
        }

        function loadCityForecast(citySlug) {
            var loader = document.getElementById('weather-widget-loader');
            if (loader) {
                loader.classList.add('is-active');
            }

            fetch(widgetUrl + '?city=' + encodeURIComponent(citySlug))
                .then(function(response) { return response.text(); })
                .then(function(html) {
                    widgetWrapper.innerHTML = html;
                    if (document.getElementById('single-forecast-slider')) {
                        initializeGlideSlider();
                    }
                })
                .catch(function(err) {
                    console.error('Failed to load city forecast:', err);
                });
        }

        // Close dropdown when clicking outside
        document.addEventListener('click', function(e) {
            if (!searchInput.contains(e.target) && !searchMenu.contains(e.target)) {
                searchMenu.parentElement.classList.remove('is-active');
            }
        });
    }
})();
