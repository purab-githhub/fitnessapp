let elapsed=0,timerHandle=null;function startTimer(){if(timerHandle)return;timerHandle=setInterval(()=>{elapsed++;const m=String(Math.floor(elapsed/60)).padStart(2,'0');const s=String(elapsed%60).padStart(2,'0');const el=document.getElementById('timer');if(el)el.textContent=`${m}:${s}`},1000)}
if('Notification' in window){window.requestFitSyncNotifications=()=>Notification.requestPermission()}
