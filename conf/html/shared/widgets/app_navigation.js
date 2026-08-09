function prepareAppOpener(type){
    document.body.classList.add("popupNavigationOpener");

    window.setTimeout(function(){
      document.body.classList.remove("popupNavigationOpener");

      let elements = document.querySelectorAll("#framework7-root > .popup");
      console.log(elements);
      if( elements.length > 0)
      {
          // mark all as known to set for the upcomming popup the size (fullzize or widget size on tablet)
          // .classList.add("popupProcessed");

          elements[elements.length-1].classList.add("popupNavigationPage");
          elements[elements.length-1].classList.add("popupNavigationRoot");
          //elements[elements.length-1].classList.add("popup-tablet-fullscreen");
      }
    }, 600);
}

function prepareAppSlide(type){
    document.body.classList.add("popupNavigationSlide");
    window.setTimeout(function(){
      document.body.classList.remove("popupNavigationSlide");

      let elements = document.querySelectorAll("#framework7-root > .popup");
      console.log(elements);
      if( elements.length > 0)
      {
          // mark all as known to set for the upcomming popup the size (fullzize or widget size on tablet)
          // .classList.add("popupProcessed");

          elements[elements.length-1].classList.add("popupNavigationPage");
          //elements[elements.length-1].classList.add("popup-tablet-fullscreen");
      }
    }, 600);
}
console.log("app navigation loaded");
