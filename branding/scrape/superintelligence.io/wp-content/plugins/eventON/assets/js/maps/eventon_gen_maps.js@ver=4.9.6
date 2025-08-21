/**
 * EventON Generate Google Maps Function
 * @version  4.9.4
 */

//return;

(function($){

// map loader function 
	$.fn.evoGenmaps = function(opt){

		var defaults = {
			delay:	0,
			fnt:	5,
			cal:	'',
			SC: 	'',
			map_canvas_id:	'',
			location_type:'',
			address:'',
			styles:'',
			zoomlevel:'',
			mapformat:'',
			scroll:false,
			iconURL:'',
			trigger_point: '',
		};
		var options = $.extend({}, defaults, opt); 

		//console.log(options);

		var geocoder;

		var code = {};
		obj = this;
		code.obj = this;

		mapBox = $('#'+options.map_canvas_id);

		code = {	
			init:function(){

				// Skip if map box isn’t visible or already drawn
                if (!mapBox.is(':visible') || mapBox.find('.gm-style').length > 0) return;

				mapBox.html( evo_general_params.html.preload_gmap);

				//if( mapBox.hasClass('mDrawn') ) return;	

				// set calendar for event
				options.cal = obj.closest('.ajde_evcal_calendar').length ? obj.closest('.ajde_evcal_calendar') : options.cal;
                code.process_SC();

				// various methods to draw map
				// load map on specified elements directly
				if(options.fnt==5){
					if(options.delay==0){	code.draw_map();	}else{
						setTimeout(code.draw_map, options.delay, this);
					}						
				}

				// deprecating rest 4.6
					// multiple maps at same time
					if(options.fnt==1){
						code.load_gmap();
					}
					
					if(options.fnt==2){
						if(options.delay==0){	code.load_gmap();	}else{
							setTimeout(code.load_gmap, options.delay, this);
						}			
					} 
					if(options.fnt==3){	code.load_gmap();	}
					
					// gmaps on popup
					if(options.fnt==4){
						// check if gmaps should run
						if( this.attr('data-gmtrig')=='1' && this.attr('data-gmap_status')!='null'){	
							code.load_gmap();			
						}	
					}				
			},
			// add unique id for map area
			process_unique_map_id: function(){
				var map_element = obj.closest('.eventon_list_event').find('.evo_metarow_gmap');
                if (!map_element.length || !map_element.attr('id')) return false;

				var map_element = obj.closest('.eventon_list_event').find('.evo_metarow_gmap');

				var randomnumber = Math.floor(Math.random() * (99 - 10 + 1)) + 10;
                options.map_canvas_id = map_element.attr('id') + '_' + randomnumber;
                map_element.attr('id', options.map_canvas_id);
                return options.map_canvas_id;
			},
			process_SC: function(){
				if (options.SC || !options.cal) return;
                options.SC = options.cal.evo_shortcode_data();
			},

			// load google map
			load_gmap: function(){
				var SC = options.SC,
                    ev_location = obj.find('.event_location_attrs'),
                    location_type = ev_location.attr('data-location_type');

				options.address = location_type == 'address' ? ev_location.attr('data-location_address') : ev_location.attr('data-latlng');
                options.location_type = location_type == 'address' ? 'add' : 'latlng';
                options.iconURL = SC && SC.mapiconurl ? SC.mapiconurl : options.iconURL;

				if (!options.address) {
                    console.log('Location address missing in options.address');
                    return false;
                }

                var map_canvas_id = code.process_unique_map_id();
                if (!map_canvas_id || !$('#' + map_canvas_id).length) {
                    console.log('Map element with id missing in page');
                    return false;
                }

                options.zoomlevel = SC && SC.mapzoom ? parseInt(SC.mapzoom) : 12;
                options.scroll = SC.mapscroll;
                options.mapformat = SC.mapformat;

                code.draw_map();
			},

			// final draw
			draw_map: function(){

				if(!options.map_canvas_id || $('body').find('#'+options.map_canvas_id).length == 0){
					console.log( 'Map element with id missing in page'); return false;
				}

				// map styles
				if( typeof gmapstyles !== 'undefined' && gmapstyles != 'default'){
					options.styles = JSON.parse(gmapstyles);
				}
				
				var myOptions = {
                    mapTypeId: options.mapformat,
                    zoom: options.zoomlevel,
                    scrollwheel: options.scroll != 'false',
                    zoomControl: true,
                    draggable: options.scroll != 'false',
                    mapId: 'DEMO_MAP_ID' 
                    // Removed mapId to allow custom styles
                };

                var map_canvas = document.getElementById(options.map_canvas_id),
                    map = new google.maps.Map(map_canvas, myOptions),
                    geocoder = new google.maps.Geocoder();
		
				// address from latlng
				if(options.location_type=='latlng' && options.address !== undefined){
					var latlngStr = options.address.split(",",2);
					var lat = parseFloat(latlngStr[0]);
					var lng = parseFloat(latlngStr[1]);
					var latlng = new google.maps.LatLng(lat, lng);

					geocoder.geocode({'latLng': latlng}, function(results, status) {
						if (status == google.maps.GeocoderStatus.OK) {				
							
							let markerOptions = {
				                map: map,
				                position: latlng
				            };

				            if (options.iconURL && options.iconURL.trim() !== '') {
				                var img = new Image();
				                img.src = options.iconURL;

				                img.onload = function () {
				                    var imgWidth = img.width;
				                    var imgHeight = img.height;

				                    var customIcon = document.createElement('div');
				                    customIcon.className = 'custom-marker';
				                    customIcon.style.width = imgWidth + 'px';
				                    customIcon.style.height = imgHeight + 'px';
				                    customIcon.style.backgroundImage = `url(${options.iconURL})`;
				                    customIcon.style.backgroundSize = 'cover';
				                    customIcon.style.position = 'absolute';

				                    markerOptions.content = customIcon;

				                    const marker = new google.maps.marker.AdvancedMarkerElement(markerOptions);
				                    map.setCenter(marker.position);
				                };

				                img.onerror = function () {
				                    console.error("Error loading marker image: " + options.iconURL);
				                    const marker = new google.maps.marker.AdvancedMarkerElement(markerOptions); // Default marker
				                    map.setCenter(marker.position);
				                };
				            } else {
				                // No custom icon, use default Google Maps marker
				                const marker = new google.maps.marker.AdvancedMarkerElement(markerOptions);
				                map.setCenter(marker.position);
				            }

						} else {				
							map_canvas.style.display = 'none';
						}
					});
					
				}else if(options.address==''){
					//console.log('t');
				}else{
					geocoder.geocode( { 'address': options.address}, function(results, status) {
						if (status == google.maps.GeocoderStatus.OK) {		
							map.setCenter(results[0].geometry.location);
                            new google.maps.Marker({
                                map: map,
                                position: results[0].geometry.location,
                                icon: options.iconURL
                            });				
							
						} else {	map_canvas.style.display = 'none';		}
					});
				}

				// mark as map drawn
				$('#'+ options.map_canvas_id).addClass('mDrawn');
			}
		}


		// INIT
		code.init();		
	};


// trigger load google map on dynamic map element u4.6.1
	$.fn.evo_load_gmap = function(opt){
		var defs = { map_canvas_id: '', delay: 0, trigger_point: '' },
            OO = $.extend({}, defs, opt),
            EL = this,
            EL_id = OO.map_canvas_id || EL.attr('id'),
            location_type = EL.data('location_type') == 'add' ? 'add' : 'latlng',
            address = location_type == 'add' ? EL.data('address') : EL.data('latlng'),
            scrollwheel = EL.data('scroll') == 'yes',
            elms = document.querySelectorAll("[id='" + EL_id + "']");

        // Ensure unique ID
        if (elms.length > 1) {
            var randomnumber = Math.floor(Math.random() * (99 - 10 + 1)) + 10;
            EL_id = EL_id + '_' + randomnumber;
            EL.attr('id', EL_id);
        }

        // Determine delay
        var __delay = OO.delay || EL.data('delay') || 0;		

        let mapData = {
            map_canvas_id: EL_id,
            fnt: 5,
            location_type: location_type,
            address: address,
            zoomlevel: parseInt(EL.data('zoom')),
            mapformat: EL.data('mty'),
            scroll: scrollwheel,
            iconURL: EL.data('mapicon') || '',
            delay: __delay,
            trigger_point: OO.trigger_point
        };

		// load the map
		EL.evoGenmaps(mapData);


	};



}(jQuery));