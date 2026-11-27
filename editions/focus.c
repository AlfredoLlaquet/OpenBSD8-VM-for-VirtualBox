/* Activate an already mapped test terminal in the disposable X11 session. */
#include <X11/Xlib.h>
#include <stdlib.h>

int main(int argc, char **argv)
{
    if (argc != 2) return 1;
    Window window = strtoul(argv[1], NULL, 0);
    Display *display = XOpenDisplay(NULL);
    if (!display || !window) return 1;
    XEvent request = {0};
    request.xclient.type = ClientMessage;
    request.xclient.window = window;
    request.xclient.message_type = XInternAtom(display, "_NET_ACTIVE_WINDOW", False);
    request.xclient.format = 32;
    request.xclient.data.l[0] = 2;
    request.xclient.data.l[1] = CurrentTime;
    XSendEvent(display, DefaultRootWindow(display), False,
               SubstructureRedirectMask | SubstructureNotifyMask, &request);
    XRaiseWindow(display, window);
    XSetInputFocus(display, window, RevertToPointerRoot, CurrentTime);
    XSync(display, False);
    XCloseDisplay(display);
    return 0;
}
