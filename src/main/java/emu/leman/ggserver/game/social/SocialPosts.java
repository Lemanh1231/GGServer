package emu.leman.ggserver.game.social;

import emu.leman.ggserver.Services;
import emu.leman.ggserver.game.economy.Currency;
import java.time.*;
import java.time.format.DateTimeFormatter;
import java.util.*;
import static emu.leman.ggserver.util.Json.*;
import static emu.leman.ggserver.game.social.SocialFollowers.*;

/** Persistent mailbox and operator send API, including account-age filtering and deletion tombstones. */
public final class SocialPosts {
    private final Services services;
    private static final String[] LANGS={"ko","en","jp","zh_chs","zh_cht","vi","es","it","id","th","pt","hi"};
    public SocialPosts(Services services) { this.services=services; }
    private List<Object> broadcasts() {
        var path=services.root.resolve("broadcast_posts.json");
        if(!java.nio.file.Files.exists(path)) return new ArrayList<>();
        Object value=emu.leman.ggserver.util.Json.read(path);
        if(!(value instanceof List<?>)) throw new IllegalStateException("Mailbox broadcast storage must be an array; refusing to overwrite");
        for(Object raw:list(value)) if(!(raw instanceof Map)||lng(map(raw).get("idx"))<=0)
            throw new IllegalStateException("Invalid mailbox broadcast record; refusing to overwrite");
        return list(value);
    }
    private static long now() { return System.currentTimeMillis()/1000; }
    private static Set<Long> deleted(Map<String,Object> user) {
        Set<Long> deleted=new LinkedHashSet<>(); for(Object id:list(user.get("deleted_post_indices"))) { long index=lng(id); if(index!=0) deleted.add(index); } return deleted;
    }
    public List<Object> getUserPosts(Map<String,Object> user) {
        synchronized(services.state) {
            if(user==null) return new ArrayList<>();
            String before=stringify(user); long now=now();
            List<Object> posts=rows(user,"posts"), broadcasts=broadcasts(); Set<Long> deleted=deleted(user), broadcastIds=new HashSet<>();
            for(Object value:broadcasts) { long id=lng(map(value).get("idx")); if(id!=0) broadcastIds.add(id); }
            long created=lng(user.get("created_at"));
            if(created==0) {
                created=lng(first(user.get("last_save_time"),now));
                try { created=LocalDate.parse(str(map(user.get("userdata")).get("u_create_time")),DateTimeFormatter.BASIC_ISO_DATE).atStartOfDay(emu.leman.ggserver.util.GameTime.ZONE).toEpochSecond(); }
                catch(RuntimeException ignored) { }
                user.put("created_at",created);
            }
            List<Object> valid=new ArrayList<>();
            for(Object value:posts) {
                if(!(value instanceof Map)) continue;
                Map<String,Object> post=map(value); long id=lng(post.get("idx")), expiry=lng(post.get("del_time"));
                if(deleted.contains(id)) continue;
                if((expiry!=0&&expiry<=now&&!truth(post.get("unlimit_flg"))) || (id!=1&&broadcastIds.contains(id)&&!truth(post.get("applies_to_new_users"))&&lng(post.get("create_time"))<created)) { if(id!=0) deleted.add(id); continue; }
                normalize(post); valid.add(post);
            }
            posts=valid;
            if(!truth(user.get("welcome_post_sent"))) {
                // Match Python even for inconsistent legacy flags/tombstones: the flag controls insertion.
                posts.addFirst(welcome(now));
                user.put("welcome_post_sent",true);
            }
            Set<Long> existing=new HashSet<>(); for(Object value:posts) existing.add(lng(map(value).get("idx")));
            for(Object value:broadcasts) {
                Map<String,Object> post=map(value); long id=lng(post.get("idx")), expiry=lng(post.get("del_time"));
                if(id==0||existing.contains(id)||deleted.contains(id)) continue;
                if(expiry!=0&&expiry<=now&&!truth(post.get("unlimit_flg"))) continue;
                if(!truth(post.get("applies_to_new_users"))&&lng(post.get("create_time"))<created) continue;
                Map<String,Object> delivery=copy(post); delivery.putIfAbsent("status",0); delivery.putIfAbsent("flg",0);
                posts.add(delivery); existing.add(id);
            }
            user.put("posts",posts); user.put("deleted_post_indices",new ArrayList<>(deleted));
            if(!before.equals(stringify(user))) services.state.saveUser(user);
            return posts;
        }
    }
    private static void normalize(Map<String,Object> post) {
        if(integer(post.get("status"))==1 || (post.containsKey("have_reward")&&integer(post.get("have_reward"))==0)) { post.put("status",1); post.put("flg",1); }
    }
    public List<Object> claim(Map<String,Object> user,long idx,int type) {
        synchronized(services.state) {
            List<Object> granted=new ArrayList<>(); if(user==null) return granted;
            // Invalid legacy rewards/capacity must not partially mutate even a direct caller's snapshot.
            Map<String,Object> original=user; user=copy(user);
            boolean all=idx==0||type==1, changed=false; double likeDelta=0;
            for(Object value:getUserPosts(user)) {
                Map<String,Object> post=map(value); if(!all&&lng(post.get("idx"))!=idx) continue;
                if(integer(post.get("have_reward"))==1) {
                    for(Object itemValue:MailboxRewards.validate(services.gameData,list(post.get("item_list")),true)) {
                        Map<String,Object> item=map(itemValue);
                        granted.add(obj("i_RewardType",integer(first(item.get("i_RewardType"),1)),"i_RewardId",integer(first(item.get("i_RewardId"),1)),"d_RewardQuantity",dbl(item.get("d_RewardQuantity"))));
                        if(!truth(item.get("already_granted"))) {
                            int rewardType=integer(item.get("i_RewardType")), rewardId=integer(item.get("i_RewardId"));
                            double quantity=dbl(item.get("d_RewardQuantity"));
                            MailboxRewards.grant(user,item);
                            if((rewardType==1||rewardType==11)&&(rewardId==3||rewardId==4)) likeDelta+=quantity;
                        }
                    }
                    post.put("have_reward",0); post.put("status",1); post.put("flg",1); changed=true;
                }
                if(!all) break;
            }
            if(changed) {
                if(Currency.parse(likeDelta).integer().signum()!=0) user.put("needs_client_reset",true);
                user.put("welcome_post_sent",true); services.state.saveUser(user);
            }
            original.clear(); original.putAll(user);
            return granted;
        }
    }
    public Map<String,Object> read(Map<String,Object> user,long idx) {
        synchronized(services.state) {
            if(user!=null) for(Object value:getUserPosts(user)) { Map<String,Object> post=map(value); if(lng(post.get("idx"))==idx) { post.put("status",1); post.put("flg",1); services.state.saveUser(user); break; } }
            return obj("idx",idx);
        }
    }
    public Map<String,Object> delete(Map<String,Object> user,long idx,int type) {
        synchronized(services.state) {
            if(user!=null) {
                getUserPosts(user); // Include lazy broadcast deliveries before protecting unclaimed mail.
                user.put("welcome_post_sent",true); Set<Long> deleted=deleted(user); List<Object> remaining=new ArrayList<>(); boolean all=idx==0||type==1;
                for(Object value:rows(user,"posts")) {
                    Map<String,Object> post=map(value); long id=lng(post.get("idx"));
                    boolean remove=integer(post.get("have_reward"))==0&&(all?(integer(post.get("status"))==1||integer(post.get("flg"))==1):id==idx);
                    if(remove) { if(id!=0) deleted.add(id); } else remaining.add(post);
                }
                if(!all&&idx!=0&&remaining.stream().noneMatch(v->lng(map(v).get("idx"))==idx)) deleted.add(idx);
                user.put("posts",remaining); user.put("deleted_post_indices",new ArrayList<>(deleted)); services.state.saveUser(user);
            }
            return obj("idx",idx);
        }
    }
    private List<Map<String,Object>> allUserContents() {
        List<Map<String,Object>> result=new ArrayList<>();
        for(Map<String,Object> row:services.state.listUserRows()) {
            Map<String,Object> contents;
            contents=map(parse(str(row.get("user_contents_json"))));
            result.add(obj("uuid",row.get("uuid"),"contents",contents));
        }
        return result;
    }
    private long nextIndex(List<Object> broadcasts,List<Map<String,Object>> users) {
        long max=100;
        for(Object value:broadcasts) max=Math.max(max,lng(map(value).get("idx")));
        var sequence=services.root.resolve("post_seq.json");
        Map<String,Object> previous=java.nio.file.Files.exists(sequence)?map(emu.leman.ggserver.util.Json.read(sequence)):obj();
        max=Math.max(max,lng(previous.get("last_idx")));
        for(Map<String,Object> row:users) {
            Map<String,Object> contents=map(row.get("contents"));
            for(Object value:list(contents.get("posts"))) max=Math.max(max,lng(map(value).get("idx")));
            for(Object value:list(contents.get("deleted_post_indices"))) max=Math.max(max,lng(value));
        }
        long watermark=Math.max(now(),lng(previous.get("last_notification_time")));
        for(Object raw:broadcasts) watermark=Math.max(watermark,notificationTime(map(raw)));
        for(var row:users) for(Object raw:list(map(row.get("contents")).get("posts"))) watermark=Math.max(watermark,notificationTime(map(raw)));
        long next=Math.addExact(max,1); write(sequence,obj("last_idx",next,"last_notification_time",Math.addExact(watermark,1))); return next;
    }
    public static long notificationTime(Map<String,Object> post) { return lng(post.getOrDefault("notification_time",post.get("create_time"))); }
    private static Object canonical(Object value) {
        if(value instanceof Map<?,?> values) {
            Map<String,Object> sorted=new TreeMap<>();
            values.forEach((key,item)->sorted.put(str(key),canonical(item))); return sorted;
        }
        if(value instanceof List<?> values) return values.stream().map(SocialPosts::canonical).toList();
        return value;
    }
    public Map<String,Object> sendPost(String uuid,Object title,Object memo,List<?> items,int noticeType,boolean appliesToNewUsers) {
        return sendPost(uuid,title,memo,items,noticeType,appliesToNewUsers,"");
    }
    public Map<String,Object> sendPost(String uuid,Object title,Object memo,List<?> items,int noticeType,boolean appliesToNewUsers,String requestId) {
        synchronized(services.state) {
            if(requestId==null) requestId="";
            if(!requestId.isEmpty()&&!requestId.matches("[A-Za-z0-9_-]{8,128}")) throw new IllegalArgumentException("Invalid mail request_id");
            boolean broadcast=uuid==null||uuid.isEmpty()||uuid.equals("all")||uuid.equals("null");
            Map<String,Object> target=broadcast?null:services.state.getUser(uuid); if(!broadcast&&target==null) return null;
            List<Object> broadcasts=broadcasts(); List<Map<String,Object>> users=allUserContents();
            List<Object> normalized=MailboxRewards.validate(services.gameData,items,true);
            String fingerprint=stringify(canonical(obj("target",broadcast?null:str(target.get("uuid")),"title",title,"memo",memo,"items",normalized,"notice_type",noticeType,"future",appliesToNewUsers)));
            List<Object> previousSends=new ArrayList<>(target==null?broadcasts:list(target.get("posts")));
            if(target!=null) previousSends.addAll(map(target.get("mail_send_requests")).values());
            if(!requestId.isEmpty()) for(Object raw:previousSends) {
                var existing=map(raw);
                if(requestId.equals(str(existing.get("request_id")))) {
                    if(!fingerprint.equals(str(existing.get("request_fingerprint")))) throw new IllegalArgumentException("request_id already used for different mail");
                    return copy(existing);
                }
            }
            long now=now(),idx=nextIndex(broadcasts,users);
            Map<String,Object> post=obj("idx",idx,"notice_type",noticeType,"have_reward",normalized.isEmpty()?0:1,"status",0,"unlimit_flg",0,"flg",0,"create_time",now,"del_time",now+86400*30L,"item_list",normalized,"url","","image_resource_name","","applies_to_new_users",appliesToNewUsers);
            post.put("notification_time",map(emu.leman.ggserver.util.Json.read(services.root.resolve("post_seq.json"))).get("last_notification_time"));
            if(!requestId.isEmpty()) {post.put("request_id",requestId);post.put("request_fingerprint",fingerprint);}
            Map<String,Object> titles=map(title),memos=map(memo);
            Object defaultTitle=title instanceof String?title:titles.getOrDefault("vi",titles.getOrDefault("en","Thông báo"));
            Object defaultMemo=memo instanceof String?memo:memos.getOrDefault("vi",memos.getOrDefault("en",""));
            for(String lang:LANGS) { post.put("title_"+lang,titles.getOrDefault(lang,defaultTitle)); post.put("memo_"+lang,memos.getOrDefault(lang,defaultMemo)); }
            if(target!=null) {
                if(!requestId.isEmpty()) {
                    var receipts=map(target.computeIfAbsent("mail_send_requests",k->obj()));
                    receipts.put(requestId,copy(post));
                }
                deliver(target,post);
            }
            else {
                broadcasts.add(post); broadcasts.removeIf(v->{Map<String,Object> b=map(v);return !truth(b.get("request_id"))&&!truth(b.get("unlimit_flg"))&&lng(b.get("del_time"))<=now;});
                write(services.root.resolve("broadcast_posts.json"),broadcasts);
                // Durable broadcast is the commit point. Cache delivery failures must not turn a
                // successful send into a retryable error: getPost reconciles missing copies later.
                int pending=0;
                for(Map<String,Object> row:users) {
                    try { Map<String,Object> user=services.state.getUser(str(row.get("uuid"))); if(user!=null) deliver(user,post); }
                    catch(RuntimeException e) { pending++; org.slf4j.LoggerFactory.getLogger(SocialPosts.class).warn("Broadcast {} committed; recipient delivery deferred",idx); }
                }
                if(pending>0) post.put("delivery_pending",pending);
            }
            return post;
        }
    }
    private void deliver(Map<String,Object> user,Map<String,Object> post) {
        long idx=lng(post.get("idx")); Set<Long> deleted=deleted(user); deleted.remove(idx); user.put("deleted_post_indices",new ArrayList<>(deleted));
        List<Object> posts=rows(user,"posts"); if(posts.stream().noneMatch(v->lng(map(v).get("idx"))==idx)) posts.add(copy(post)); services.state.saveUser(user);
    }
    private static Map<String,Object> welcome(long now) {
        Map<String,Object> post=obj("idx",1,"notice_type",1,"have_reward",1,"status",0,"unlimit_flg",0,"flg",0,"create_time",now,"del_time",now+86400*30L,"item_list",new ArrayList<>(List.of(obj("i_RewardType",1,"i_RewardId",1,"d_RewardQuantity",1000.0),obj("i_RewardType",1,"i_RewardId",2,"d_RewardQuantity",500.0))),"url","","image_resource_name","");
        String[][] localized={
            {"기타소녀에 오신 것을 환영합니다!","기타소녀와 함께 힐링 음악 여행을 떠나보세요."},
            {"Welcome to Guitar Girl!","Thank you for playing Guitar Girl! Enjoy your peaceful guitar melodies."},
            {"ギター少女へようこそ！","ギター少女と一緒に心癒される音楽の旅へ。"},
            {"欢迎来到吉他少女！","欢迎和吉他少女一起开启治愈音乐之旅。"},
            {"歡迎來到吉他少女！","歡迎和吉他少女一起開啟療癒音樂之旅。"},
            {"Chào mừng đến với Guitar Girl!","Cảm ơn bạn đã tham gia cùng cô gái guitar! Chúc bạn có những phút giây thư giãn tuyệt vời cùng âm nhạc."},
            {"¡Te damos la bienvenida a Guitar Girl!","¡Disfruta de la música relajante junto a Guitar Girl!"},
            {"Benvenuta in Guitar Girl!","Goditi la musica rilassante con Guitar Girl!"},
            {"Selamat datang di Gadis Gitar!","Nikmati musik santai bersama Gadis Gitar!"},
            {"ยินดีต้อนรับสู่สาวนักกีตาร์!","เพลิดเพลินไปกับเสียงเพลงอันผ่อนคลายกับสาวนักกีตาร์!"},
            {"Bem-vindo ao Menina guitarrista!","Aproveite a música relaxante com a Menina guitarrista!"},
            {"गिटार गर्ल में आपका स्वागत है!","गिटार गर्ल के साथ मधुर संगीत का आनंद लें।"}
        };
        for(int i=0;i<LANGS.length;i++) { post.put("title_"+LANGS[i],localized[i][0]); post.put("memo_"+LANGS[i],localized[i][1]); }
        return post;
    }
}
