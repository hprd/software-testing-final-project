package java.nio.file;

import java.util.Objects;
import java.util.Spliterator;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Consumer;
import java.util.stream.Stream;
import java.util.stream.StreamSupport;

/** Research fixture for two sequential listings of one stable default-filesystem directory. */
public final class FilesListWitness {
    private static final AtomicInteger MATCHED = new AtomicInteger();

    private FilesListWitness() { }

    public static Stream<Path> wrap(Stream<Path> original, Path directory) {
        String target = System.getProperty("fileslist.fixture.directory");
        if (target == null || directory.getFileSystem() != FileSystems.getDefault()
                || !directory.toAbsolutePath().normalize().equals(Path.of(target).toAbsolutePath().normalize())
                || !selectedCaller()) {
            return original;
        }
        int call = MATCHED.incrementAndGet();
        boolean swap = call % 2 == 0;
        System.err.println("FILES_LIST_FIXTURE call=" + call + " action=" + (swap ? "swap-first-pair" : "identity"));
        Stream<Path> result = swap ? swapFirstPair(original) : original;
        AtomicBoolean seen = new AtomicBoolean();
        return result.peek(path -> {
            if (seen.compareAndSet(false, true)) {
                System.err.println("FILES_LIST_FIRST call=" + call + " path=" + path);
            }
        });
    }

    private static boolean selectedCaller() {
        if (Boolean.getBoolean("fileslist.fixture.controls")) return true;
        for (StackTraceElement frame : Thread.currentThread().getStackTrace()) {
            if (frame.getClassName().equals("org.apache.commons.io.function.IOBinaryOperatorStreamTest")
                    && frame.getMethodName().equals("testReduce")) return true;
        }
        return false;
    }

    /** Lazy two-entry look-ahead; public solely for focused fixture controls. */
    public static Stream<Path> swapFirstPair(Stream<Path> original) {
        Spliterator<Path> input = original.spliterator();
        Spliterator<Path> reordered = new Spliterator<Path>() {
            private boolean initialized;
            private Path pending;
            private boolean hasPending;

            @Override
            public boolean tryAdvance(Consumer<? super Path> action) {
                Objects.requireNonNull(action);
                if (!initialized) {
                    initialized = true;
                    boolean first = input.tryAdvance(path -> pending = path);
                    if (!first) return false;
                    Path[] second = new Path[1];
                    if (input.tryAdvance(path -> second[0] = path)) {
                        hasPending = true;
                        action.accept(second[0]);
                    } else {
                        Path only = pending;
                        pending = null;
                        action.accept(only);
                    }
                    return true;
                }
                if (hasPending) {
                    Path first = pending;
                    pending = null;
                    hasPending = false;
                    action.accept(first);
                    return true;
                }
                return input.tryAdvance(action);
            }

            @Override
            public Spliterator<Path> trySplit() { return null; }

            @Override
            public long estimateSize() { return Long.MAX_VALUE; }

            @Override
            public int characteristics() {
                return input.characteristics() & ~(Spliterator.SORTED | Spliterator.SIZED | Spliterator.SUBSIZED);
            }
        };
        // No traversal at construction. Closing this stream closes the original directory stream.
        return StreamSupport.stream(reordered, false).onClose(original::close);
    }
}
