/**
 * Salient Social.
 *
 * @author ThemeNectar
 */
 /* global jQuery */
 
jQuery(document).ready(function ($) {
  
  "use strict";
  
  function NectarSocial() {
    
    this.$body              = $('body');
    this.$window            = $(window);
    this.$wpAdminBar        = $('#wpadminbar');
    this.usingMobileBrowser = (navigator.userAgent.match(/(Android|iPod|iPhone|iPad|BlackBerry|IEMobile|Opera Mini)/)) ? true : false;
    
    // Events.
    this.mouseEvents();
    
    // Nectar Love
    this.nectarLove();
    
    // Fixed to bottom social sharing style.
    if( $('body').find('.nectar-social.fixed').length > 0 ) {
      this.fixedStyle();
    }
    
  }
  
  
  NectarSocial.prototype.mouseEvents = function() {
    
    this.$body.on('click', '#single-below-header .nectar-social a', function () {
      return false;
    });
    
    $('body.single-product .nectar-social').addClass('woo');
    
    this.$body.on('click', '.facebook-share:not(.inactive)', this.facebookShare);
    this.$body.on('click', '.nectar-social:not(".woo") .twitter-share:not(.inactive)', this.twitterShare);
    this.$body.on('click', '.nectar-social.woo .twitter-share', this.wooTwitterShare);
    this.$body.on('click', '.nectar-social:not(".woo") .linkedin-share:not(.inactive)', this.linkedInShare);
    this.$body.on('click', '.nectar-social.woo .linkedin-share', this.woolinkedInShare);
    this.$body.on('click', '.nectar-social:not(".woo") .pinterest-share:not(.inactive)', this.pinterestShare);
    this.$body.on('click', '.nectar-social.woo .pinterest-share', this.wooPinterestShare);
    
    this.$body.on('click', '.nectar-social.fixed > a', function () {
      return false;
    });
    
    
    // Hover style
    // desktop
    if (!this.usingMobileBrowser) {
      
      var $socialTimeout;
      this.$body.on('mouseenter', '.nectar-social.hover .share-btn', function () {
        
        clearTimeout($socialTimeout);
        
        
        // Hide other sibling items when needed.
        if( $(this).parents('[id*="-meta"]').length > 0 ) {
          $(this).parents('[id*="-meta"]').addClass('social-hovered');
        }
        if( $(this).parents('#single-below-header').length > 0 ) {
          $(this).parents('#single-below-header').addClass('social-hovered');
        }
        
        $(this).parent().addClass('visible');
        
        
      });
      
      
      this.$body.on('mouseleave', '.nectar-social.hover', function () {
        
        var $that = $(this);
        
        $socialTimeout = setTimeout(function () {
          
          $that.removeClass('visible');
          
          if( $that.parents('[id*="-meta"]').length > 0 ) {
            $that.parents('[id*="-meta"]').removeClass('social-hovered');
          }
          if( $that.parents('#single-below-header').length > 0 ) {
            $that.parents('#single-below-header').removeClass('social-hovered');
          }
          
        }, 200);
        
      });
      
    } 
    
    // Click triggered on mobile
    else {
      
      this.$body.on('click', '.nectar-social.hover .share-btn', function () {
        
        // Hide other sibling items when needed.
        if( $(this).parents('[id*="-meta"]').length > 0 ) {
          $(this).parents('[id*="-meta"]').addClass('social-hovered');
        }
        if( $(this).parents('#single-below-header').length > 0 ) {
          $(this).parents('#single-below-header').addClass('social-hovered');
        }
        
        $(this).parent().addClass('visible');
        
        return false;
      });
      
    }
    
    
  };
  
  
  
  
  NectarSocial.prototype.facebookShare = function() {
    var windowLocation = window.location.href.replace(window.location.hash, '');
    window.open('https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(windowLocation), "facebookWindow", "height=380,width=660,resizable=0,toolbar=0,menubar=0,status=0,location=0,scrollbars=0");
    return false;
  };
  
  
  NectarSocial.prototype.twitterShare = function() {
    var windowLocation = window.location.href.replace(window.location.hash, '');
    var $pageTitle;
    
    if ($(".section-title h1").length > 0) {
      $pageTitle = encodeURIComponent($(".section-title h1").text());
    } else {
      $pageTitle = encodeURIComponent($(document).find("title").text());
    }
    window.open('https://twitter.com/intent/tweet?text=' + $pageTitle + ' ' + windowLocation, "twitterWindow", "height=380,width=660,resizable=0,toolbar=0,menubar=0,status=0,location=0,scrollbars=0");
    return false;
  };
  
  NectarSocial.prototype.wooTwitterShare = function() {
    var windowLocation = window.location.href.replace(window.location.hash, '');
    window.open('https://twitter.com/intent/tweet?text=' + $("h1.product_title").text() + ' ' + encodeURIComponent(windowLocation), "twitterWindow", "height=380,width=660,resizable=0,toolbar=0,menubar=0,status=0,location=0,scrollbars=0");
    return false;
  };
  
  NectarSocial.prototype.linkedInShare = function() {
    var windowLocation = window.location.href.replace(window.location.hash, '');
    var $pageTitle;
    
    if ($(".section-title h1").length > 0) {
      $pageTitle = encodeURIComponent($(".section-title h1").text());
    } else {
      $pageTitle = encodeURIComponent($(document).find("title").text());
    }
    window.open('https://www.linkedin.com/sharing/share-offsite/?mini=true&url=' + encodeURIComponent(windowLocation) + '&title=' + $pageTitle + '', "linkedInWindow", "height=480,width=660,resizable=0,toolbar=0,menubar=0,status=0,location=0,scrollbars=0");
    return false;
  };
  
  NectarSocial.prototype.woolinkedInShare = function() {
    var windowLocation = window.location.href.replace(window.location.hash, '');
    window.open('https://www.linkedin.com/sharing/share-offsite/?mini=true&url=' + encodeURIComponent(windowLocation) + '&title=' + $("h1.product_title").text(), "twitterWindow", "height=380,width=660,resizable=0,toolbar=0,menubar=0,status=0,location=0,scrollbars=0");
    return false;
  };
  
  NectarSocial.prototype.pinterestShare = function() {
    var windowLocation = window.location.href.replace(window.location.hash, '');
    var $sharingImg = ($('.single-portfolio').length > 0 && $('div[data-featured-img]').attr('data-featured-img') != 'empty') ? $('div[data-featured-img]').attr('data-featured-img') : $('#ajax-content-wrap img').first().attr('src');
    if ( $sharingImg ) {
      $sharingImg = encodeURIComponent($sharingImg);
    }
    var $pageTitle;
    
    if ($(".section-title h1").length > 0) {
      $pageTitle = encodeURIComponent($(".section-title h1").text());
    } else {
      $pageTitle = encodeURIComponent($(document).find("title").text());
    }
    
    window.open('https://pinterest.com/pin/create/button/?url=' + encodeURIComponent(windowLocation) + '&media=' + $sharingImg + '&description=' + $pageTitle, "pinterestWindow", "height=640,width=660,resizable=0,toolbar=0,menubar=0,status=0,location=0,scrollbars=0");
    return false;
  };
  
  NectarSocial.prototype.wooPinterestShare = function () {
    var $imgToShare = ($('img.attachment-shop_single').length > 0) ? $('img.attachment-shop_single').first().attr('src') : $('.single-product-main-image img').first().attr('src');
    if ( $imgToShare ) {
      $imgToShare = encodeURIComponent($imgToShare);
    }
    var windowLocation = window.location.href.replace(window.location.hash, '');
    window.open('https://pinterest.com/pin/create/button/?url=' + encodeURIComponent(windowLocation) + '&media=' + $imgToShare + '&description=' + $('h1.product_title').text(), "pinterestWindow", "height=640,width=660,resizable=0,toolbar=0,menubar=0,status=0,location=0,scrollbars=0");
    return false;
  };
  
  
  NectarSocial.prototype.nectarLove = function() {
    
    this.$body.on('click', '.nectar-love', function () {
      
      var $loveLink = $(this),
      $id           = $(this).attr('id'),
      $that         = $(this);
      
      if ($loveLink.hasClass('loved') || $(this).hasClass('inactive')) {
        return false;
      }
      
      var $dataToPass = {
        action: 'nectar-love',
        loves_id: $id,
        love_nonce: window.nectarLove.loveNonce
      };
      
      $.post(window.nectarLove.ajaxurl, $dataToPass, function (data) {
        $loveLink.find('.nectar-love-count').html(data);
        $loveLink.addClass('loved').attr('title', 'You already love this!');
        $that.find('.icon-salient-heart-2').addClass('loved');
      });
      
      $(this).addClass('inactive');
      
      return false;
    });
    
  };
  
  
  
  NectarSocial.prototype.fixedStyle = function() {
    
    // Move DOM postiion.
    $('.wpb_wrapper .nectar-social.fixed').each(function(i){
      
      // Remove any after first instance.
      if( i !== 0 ) {
        $(this).remove();
      } else {
        
        var $fixedMarkup = $(this).clone();
        $('body').append($fixedMarkup);
        $(this).remove();
      }
      
    });
    
    function showFixedSharing() {

      if ( $(window).scrollTop() > 150) {
        
        $('.nectar-social.fixed').addClass('visible');
        
        $(window).off('scroll', showFixedSharing);
        $(window).on('scroll', hideFixedSharing);
      }
      
    }
    
    function hideFixedSharing() {
      
      if ( $(window).scrollTop() < 150) {
        
        $('.nectar-social.fixed').removeClass('visible');
        
        $(window).off('scroll', hideFixedSharing);
        $(window).on('scroll', showFixedSharing);
      }
      
    }
    
    if( $('.nectar-social.fixed').length > 0 ) {
      
      if ( $(window).width() < 1000 ) {
        if ( $(window).scrollTop() > 150) {
          $(window).on('scroll', hideFixedSharing);
        } else {
          $(window).on('scroll', showFixedSharing);
        }
      }
      
      $(window).on('smartresize',function () {
        
        if ( $(window).width() > 1000) {
          $('.nectar-social.fixed').addClass('visible');
        } else if ( $(window).scrollTop() < 150) {
          $(window).off('scroll', hideFixedSharing);
          $(window).on('scroll', showFixedSharing);
          $('.nectar-social.fixed').removeClass('visible');
        } else {
          $(window).off('scroll', showFixedSharing);
          $(window).on('scroll', hideFixedSharing);
        }
        
      });
      
    }
    
  };
  
  
  var nectarSocialInit = new NectarSocial();
  
  window.NectarSocial = NectarSocial;
  
  
});