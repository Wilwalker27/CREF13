function connectSocket(onRefresh) {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${protocol}://${window.location.host}/ws`);

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === "refresh" && typeof onRefresh === "function") {
        onRefresh();
      }
    } catch (error) {
      console.error("WS parse error", error);
    }
  };

  ws.onclose = () => {
    setTimeout(() => connectSocket(onRefresh), 1500);
  };
}
