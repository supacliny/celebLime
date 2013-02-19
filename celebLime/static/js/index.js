// view toggle
$('.toggleview').on('click', function(event){
  event.preventDefault();

  if($(event.target).attr('id') == "list"){
    $('.toggleview #list').addClass('current');
    $('.toggleview #grid').removeClass('current');
    $('.main').addClass('list');
    $('.main').removeClass('grid');
  } else{
    $('.toggleview #grid').addClass('current');
    $('.toggleview #list').removeClass('current');
    $('.main').removeClass('list');
    $('.main').addClass('grid');
  }
});


// scrolling detection for top profile bar
$(window).scroll(function(){
  if($('body').scrollTop() >= 570 || $('html').scrollTop() >= 570){
    $('#infobar').show();
  } else {
    $('#infobar').hide();
  }
});


// spotify player
$(document).on('click', '.music-links .spotify',function(event){
  event.preventDefault();

    $('#spotifyplayer .close').click();

  var player = '<a href="#" class="slide"><br />&raquo;</a><a href="#" class="close">x</a><iframe src="https://embed.spotify.com/?uri='+$(this).attr('href')+'&theme=white&view=list" width="300" height="380" frameborder="0" allowtransparency="true"></iframe>';
  var container = $('<div id="spotifyplayer"></div>');
  container.html(player);

  container.appendTo('body');
  container.animate({
    'right':0
  }, 500, function(){
    // add event for slide link
    $('#spotifyplayer .slide').on('click', function(event){
      event.preventDefault();

      // if player is fully exposed
      if($('#spotifyplayer').css('right') == '0px'){
        $('#spotifyplayer .slide').html('<br />&laquo;');
        $('#spotifyplayer').animate({
          'right': '-320px'
        }, 500);
      } else {
        $('#spotifyplayer .slide').html('<br />&raquo;');
        $('#spotifyplayer').animate({
          'right': '-0px'
        }, 500);
      }
    });



    // add event for close link
    $('#spotifyplayer .close').on('click', function(event){
      event.preventDefault();
      // animate slide out
      $('#spotifyplayer').animate({
        'right':'-320px'
      }, 500, function(){
        // remove from dom
        $('#spotifyplayer').remove();
      });
    });
  });
});


// youtube player
$(document).on('click','.music-links .youtube', function(event){
  event.preventDefault();
  var playerHeight = $(window).height() - 80 - 130 // compensate for main nav and thumbnails at bottom
  var track = $(this).attr('data-track'),
    artist = $(this).attr('data-artist');


  // will contain the whole shebang
  var container = $('<div id="youtubeplayer"></div>');
  container.css({'height':playerHeight});


  // will hold video and info
  var vid = $('<div class="videoholder"></div>');
  vid.html('<iframe src="http://www.youtube.com/embed/'+$(this).attr('href')+'" frameborder="0" allowfullscreen></iframe>');

  // set up the info pane
  var videoInfo = $('<div class="videoinfo"></div>');
  videoInfo.html('<div class="title">'+track+'</div><div class="artist">'+artist+'</div><a href="#" class="share"></a><a href="#" class="close"></a>');


  // set up thumbnails
  var thumbnails = $('<div class="videothumbnails"></div>');
    // parse JSON elements and add to ul with event handlers?



  videoInfo.appendTo(vid);
  vid.appendTo(container);
  thumbnails.appendTo(container);

  container.appendTo('body');

  container.animate({
    'opacity':1
  }, 500, function(){
    $('#youtubeplayer .close').on('click', function(event){
      event.preventDefault();
      //animate out
      $('#youtubeplayer').animate({
        'opacity': 0
      }, 500, function(){
        $('#youtubeplayer').remove();
      });
    });
  });

});




