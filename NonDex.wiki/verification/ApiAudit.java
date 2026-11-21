import java.io.*;
import java.lang.annotation.*;
import java.lang.reflect.*;
import java.nio.file.*;
import java.text.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.function.Supplier;
import edu.illinois.nondex.common.NonDex;

/** Runtime coverage probes; use verify.py. Does not certify API contract validity. */
public class ApiAudit {
    @Retention(RetentionPolicy.RUNTIME) @interface A {}
    @Retention(RetentionPolicy.RUNTIME) @interface B {}
    @Retention(RetentionPolicy.RUNTIME) @interface C {}
    @Retention(RetentionPolicy.RUNTIME) @Repeatable(Tags.class) @interface Tag { int value(); }
    @Retention(RetentionPolicy.RUNTIME) @interface Tags { Tag[] value(); }
    @A @B @C public static class Subject {
        @A @B @C @Tag(1) @Tag(2) @Tag(3) public int first;
        public int second, third;
        public Subject() {} public Subject(int x) {} public Subject(String x) {}
        public class X {} public class Y {} public class Z {}
        @A @B @C @Tag(1) @Tag(2) @Tag(3) public void method(@A @B @C int x, @A @B @C String y)
                throws IOException, ReflectiveOperationException, InterruptedException {}
        public void other() {} public void another() {}
    }
    static String render(Object value) {
        if (value instanceof Object[]) return Arrays.deepToString((Object[]) value);
        return String.valueOf(value);
    }
    static Object[] consume(Iterator<?> it) {
        List<Object> out = new ArrayList<>();
        it.forEachRemaining(out::add);
        return out.toArray();
    }
    static String canonical(Object value) {
        if (value instanceof Object[]) {
            List<String> parts = new ArrayList<>();
            for (Object x : (Object[]) value) parts.add(canonical(x));
            Collections.sort(parts);
            return parts.toString();
        }
        return String.valueOf(value);
    }
    static void probe(String name, Supplier<?> call, boolean preserveMembers) {
        probe(name, call, preserveMembers, null);
    }
    static void probe(String name, Supplier<?> call, boolean preserveMembers, String knownMembers) {
        // Warm up lazy JDK initialization before measuring NonDex choices.
        Object original = call.get();
        String expected = knownMembers == null ? canonical(original) : knownMembers;
        Set<String> outputs = new TreeSet<>();
        int choices = 0;
        int violations = 0;
        String firstFailure = "";
        for (int i = 0; i < 24; i++) {
            int before = NonDex.getInstance().getPossibleExplorations();
            Object value = call.get();
            choices += NonDex.getInstance().getPossibleExplorations() - before;
            outputs.add(render(value));
            if (preserveMembers && !expected.equals(canonical(value))) {
                violations++;
                if (firstFailure.isEmpty()) firstFailure = "expected=" + expected + "; actual=" + canonical(value);
            }
        }
        System.out.println("PROBE\t" + name + "\t" + choices + "\t" + outputs.size()
                + "\t" + violations + "\t" + firstFailure);
    }
    public static void main(String[] args) throws Exception {
        // Initialize the same singleton used by injected calls, including on plain runs.
        NonDex.getInstance().getPossibleExplorations();
        Path dir = Files.createTempDirectory("nondex-api-audit-");
        try {
            for (int i = 0; i < 5; i++) Files.createFile(dir.resolve("file" + i));
            File f = dir.toFile();
            probe("File.list()", () -> f.list(), true);
            probe("File.list(FilenameFilter)", () -> f.list((d,n) -> true), true);
            probe("File.listFiles()", () -> f.listFiles(), true);
            probe("File.listFiles(FilenameFilter)", () -> f.listFiles((FilenameFilter)(d,n) -> true), true);
            probe("File.listFiles(FileFilter)", () -> f.listFiles((FileFilter)x -> true), true);
            probe("File.listRoots()", File::listRoots, true);
            Class<?> cl = Subject.class;
            for (String name : new String[]{"getClasses", "getDeclaredClasses", "getFields",
                    "getDeclaredFields", "getMethods", "getDeclaredMethods", "getConstructors",
                    "getDeclaredConstructors", "getAnnotations", "getDeclaredAnnotations"}) {
                Method m = Class.class.getMethod(name);
                probe("Class." + name + "()", () -> {
                    try { return m.invoke(cl); } catch (Exception e) { throw new RuntimeException(e); }
                }, true);
            }
            Method m = cl.getMethod("method", int.class, String.class);
            probe("Method.getExceptionTypes()", m::getExceptionTypes, true);
            probe("Method.getGenericExceptionTypes()", m::getGenericExceptionTypes, true);
            probe("Method.getDeclaredAnnotations()", m::getDeclaredAnnotations, true);
            probe("Method.getParameterAnnotations()", m::getParameterAnnotations, true);
            probe("Method.getAnnotations()", m::getAnnotations, true);
            probe("Method.getAnnotationsByType(Tag.class)", () -> m.getAnnotationsByType(Tag.class), true);
            probe("Method.getDeclaredAnnotationsByType(Tag.class)", () -> m.getDeclaredAnnotationsByType(Tag.class), true);
            Field field = cl.getField("first");
            probe("Field.getDeclaredAnnotations()", field::getDeclaredAnnotations, true);
            probe("Field.getAnnotationsByType(Tag.class)", () -> field.getAnnotationsByType(Tag.class), true);
            probe("Field.getAnnotations()", field::getAnnotations, true);
            probe("Field.getDeclaredAnnotationsByType(Tag.class)", () -> field.getDeclaredAnnotationsByType(Tag.class), true);
            probe("BreakIterator.getAvailableLocales()", BreakIterator::getAvailableLocales, true);
            probe("Collator.getAvailableLocales()", Collator::getAvailableLocales, true);
            probe("DateFormat.getAvailableLocales()", DateFormat::getAvailableLocales, true);
            probe("DateFormatSymbols.getAvailableLocales()", DateFormatSymbols::getAvailableLocales, true);
            probe("DecimalFormatSymbols.getAvailableLocales()", DecimalFormatSymbols::getAvailableLocales, true);
            DateFormatSymbols symbols = new DateFormatSymbols(Locale.US);
            String[][] baseZones = symbols.getZoneStrings();
            probe("DateFormatSymbols.getZoneStrings()", () -> {
                String[][] zones = symbols.getZoneStrings();
                if (zones.length != baseZones.length) throw new AssertionError("zone rows");
                for (int i = 0; i < zones.length; i++) {
                    // This runtime's original rows have seven entries.
                    if (zones[i].length != 7 && zones[i].length != 8) throw new AssertionError("zone columns");
                    if (!Arrays.equals(Arrays.copyOf(zones[i], 7), Arrays.copyOf(baseZones[i], 7)))
                        throw new AssertionError("zone content");
                    if (zones[i].length == 8 && zones[i][7] != null) throw new AssertionError("zone extension");
                }
                return zones;
            }, false);
            List<String> held = Arrays.asList("a", "b", "c", "d", "e", "f");
            List<Map<String,String>> maps = Arrays.asList(new HashMap<>(), new WeakHashMap<>(),
                    new IdentityHashMap<>(), new ConcurrentHashMap<>());
            for (Map<String,String> map : maps) {
                for (String s : held) map.put(s,s);
                String type = map.getClass().getSimpleName();
                for (String view : Arrays.asList("entrySet", "keySet", "values")) {
                    Collection<?> values = view.equals("entrySet") ? map.entrySet()
                            : view.equals("keySet") ? map.keySet() : map.values();
                    probe(type + "." + view + "().iterator()", () -> consume(values.iterator()), true);
                    probe(type + "." + view + "().toArray()", values::toArray, true);
                    probe(type + "." + view + "().toArray(T[])", () -> values.toArray(new Object[0]), true);
                    probe(type + "." + view + "().forEach()", () -> {
                        List<Object> out = new ArrayList<>(); values.forEach(out::add); return out.toArray();
                    }, true);
                    probe(type + "." + view + "().spliterator()", () -> {
                        List<Object> out = new ArrayList<>(); values.spliterator().forEachRemaining(out::add); return out.toArray();
                    }, true);
                    probe(type + "." + view + "().toString()", values::toString, false);
                    probe(type + "." + view + "().stream()", () -> values.stream().toArray(), true);
                    probe(type + "." + view + "().parallelStream()", () -> values.parallelStream().toArray(),
                            true, canonical(consume(values.iterator())));
                }
                probe(type + ".toString()", map::toString, false);
                probe(type + ".forEach()", () -> {
                    List<String> out = new ArrayList<>(); map.forEach((k,v) -> out.add(k)); return out.toArray();
                }, true);
                if (map instanceof ConcurrentHashMap) {
                    ConcurrentHashMap<String,String> cm = (ConcurrentHashMap<String,String>) map;
                    probe("ConcurrentHashMap.keys()", () -> Collections.list(cm.keys()).toArray(), true);
                    probe("ConcurrentHashMap.elements()", () -> Collections.list(cm.elements()).toArray(), true);
                }
            }
            List<Collection<String>> collections = Arrays.asList(new HashSet<>(held),
                    new PriorityQueue<>(held), new PriorityBlockingQueue<>(held));
            for (Collection<String> col : collections) collectionProbes(col);
            DelayQueue<Item> delay = new DelayQueue<>();
            for (int i = 0; i < 6; i++) delay.add(new Item(i));
            collectionProbes(delay);
            Hashtable<String,String> table = new Hashtable<>();
            for (String s : held) table.put(s,s);
            probe("Hashtable.keys()", () -> Collections.list(table.keys()).toArray(), true);
            Object obj = new Object();
            probe("Object.hashCode()", obj::hashCode, true);
            probe("System.identityHashCode(Object)", () -> System.identityHashCode(obj), true);
            probe("Files.list(Path)", () -> {
                try (java.util.stream.Stream<Path> stream = Files.list(dir)) { return stream.toArray(); }
                catch (IOException e) { throw new UncheckedIOException(e); }
            }, true);
        } finally {
            try (java.util.stream.Stream<Path> stream = Files.list(dir)) {
                for (Path p : (Iterable<Path>)stream::iterator) Files.delete(p);
            }
            Files.delete(dir);
        }
    }
    static void collectionProbes(Collection<?> col) {
        String name = col.getClass().getSimpleName();
        probe(name + ".iterator()", () -> consume(col.iterator()), true);
        probe(name + ".toArray()", col::toArray, true);
        probe(name + ".toArray(T[])", () -> col.toArray(new Object[0]), true);
        probe(name + ".toString()", col::toString, false);
        probe(name + ".forEach()", () -> {
            List<Object> out = new ArrayList<>(); col.forEach(out::add); return out.toArray();
        }, true);
        probe(name + ".spliterator()", () -> {
            List<Object> out = new ArrayList<>(); col.spliterator().forEachRemaining(out::add); return out.toArray();
        }, true);
        probe(name + ".stream()", () -> col.stream().toArray(), true);
        probe(name + ".parallelStream()", () -> col.parallelStream().toArray(), true);
    }
    static class Item implements Delayed {
        final int value; Item(int value) { this.value = value; }
        public long getDelay(TimeUnit unit) { return 0; }
        public int compareTo(Delayed other) { return 0; }
        public String toString() { return Integer.toString(value); }
    }
}
