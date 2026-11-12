package emu.leman.ggserver.net;


/** Packet handler adapted into the existing registry, including its account locking. */
public abstract class NetHandler {
    private final String command;

    protected NetHandler(String command) { this.command=command; }
    public final String command() { return command; }
    public abstract Result handle(GamePacket packet);

    public final void register(HandlerRegistry registry) {
        registry.register(command,(request,context) -> handle(new GamePacket(command,request,context)));
    }
}
