var jc;

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
function onYouTubeIframeAPIReady() {
    //maybe do something here later
}

$(document).on('click','.music-links .youtube', function(event){

  event.preventDefault();
  var playerHeight = $(window).height() - 80 - 130; // compensate for main nav and thumbnails at bottom
  var track = $(this).attr('data-track'),
    artist = $(this).attr('data-artist');

    var ytplist = $(this).attr("data-playlist");
    ytplist = eval(ytplist);

  // will contain the whole shebang
  var container = $('<div id="youtubeplayer"></div>');
  container.css({'height':playerHeight});

    var vidID = $(this).attr('href');
    vidIDs = ytplist;
    allvidIDs = vidIDs.slice(0);
    allvidIDs.shift(5);
    vidIDs.shift(1);

  // will hold video and info
  var vid = $('<div class="videoholder"><div id="ytPlayer"></div></div>');
  //vid.html('<iframe src="http://www.youtube.com/embed/'+$(this).attr('href')+'?enablejsapi=1&rel=0&showinfo=0&autoplay=1&playlist='+ ytplist.slice(1).join() +'" frameborder="0" allowfullscreen></iframe>');

  // set up the info pane
  var videoInfo = $('<div class="videoinfo"></div>');
  videoInfo.html('<div class="title">'+track+'</div><div class="artist">'+artist+'</div><a href="#" class="share"></a><a href="#" class="close"></a>');


  // set up thumbnails
  var thumbnails = $('<div class="videothumbnails"><a href="#" class="yt-prev"></a><a href="#" class="yt-next"></a></div>');
  genYoutubeThumbs(ytplist).appendTo(thumbnails);


  // combine everything
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


    //youtube stuff
    //var player;
    player = new YT.Player('ytPlayer', {
        height: playerHeight,
        width: '640',
        videoId: vidID,
        playerVars: {playlist:[vidIDs]},
        events: {
            'onReady': onPlayerReady,
            'onStateChange': onPlayerStateChange
        }
    });

    function onPlayerReady(event) {
        //player.loadPlaylist(vidIDs);
        //player.setLoop(false);
        event.target.playVideo();
    }
    function onPlayerStateChange(event) {
        console.log(event.data);
    }
    function stopVideo() {
        player.stopVideo();
    }


});

// generate jquery object that contains the thumbnails of related videos
// replace/modify this with your JSON parsing or etc
function genYoutubeThumbs(plist){
  // junk variables for demo/testing purposes... should be replaced with JSON value
    var tempimage = '../static/img/albumart/thumbnail.jpg',
      count = 12;

    count = plist.length;


  // set up jquery fun
  var container = $('<div class="container thumbs"></div>');
  var list = $('<ul></ul>');

  for(var i=0; i<count; i++){
    var thumbnail = $('<li class="thumbnail"></li>');
    thumbnail.css({'background-image':'url("http://img.youtube.com/vi/' + plist[i] + '/default.jpg")'});
    thumbnail.html('<a href="#"></a>');
    thumbnail.appendTo(list);
  }
  list.appendTo(container);
  return container;
}

$(document).on('click', '.videothumbnails', function(event){
  event.preventDefault();

  var totalItems = $('.thumbs ul li').length - 1,
  max = totalItems * -232,
  clicked = $(event.target).attr('class'),
  currentPos = parseInt($('.thumbs ul').css('left'));


  if(clicked == 'yt-next' && currentPos <= totalItems){
    var newLocation = currentPos - 1160;

    if(newLocation >= max){
      $('.thumbs ul').animate({
       'left':newLocation.toString()+'px'
       });
    }
  }

  if(clicked == 'yt-prev' && currentPos != '0px'){
    var newLocation = currentPos + 1160;

    if(newLocation <= 0){
      $('.thumbs ul').animate({
      'left': newLocation.toString()+'px'
      }, 500);
    }
  }
});
