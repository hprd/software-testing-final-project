import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.FilesListWitness;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Spliterator;
import java.util.Spliterators;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Consumer;
import java.util.stream.Collectors;
import java.util.stream.Stream;
import java.util.stream.StreamSupport;

/** Checks fixture invariants independently of the Commons IO assertion. */
public final class Check {
    private static void require(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    private static Stream<Path> source(AtomicInteger reads, AtomicInteger closes) {
        List<Path> values = Arrays.asList(Path.of("a"), Path.of("b"), Path.of("c"), Path.of("d"));
        Spliterator<Path> input = new Spliterators.AbstractSpliterator<Path>(Long.MAX_VALUE, Spliterator.DISTINCT) {
            int position;
            @Override
            public boolean tryAdvance(Consumer<? super Path> action) {
                if (position == values.size()) return false;
                reads.incrementAndGet();
                action.accept(values.get(position++));
                return true;
            }
        };
        return StreamSupport.stream(input, false).onClose(closes::incrementAndGet);
    }

    private static void syntheticControls() {
        AtomicInteger reads = new AtomicInteger();
        AtomicInteger closes = new AtomicInteger();
        Stream<Path> reordered = FilesListWitness.swapFirstPair(source(reads, closes));
        require(reads.get() == 0, "construction must not traverse");
        require(reordered.findFirst().get().equals(Path.of("b")), "first pair must swap");
        require(reads.get() == 2, "short circuit must read exactly two upstream entries");
        require(closes.get() == 0, "terminal operation must not implicitly close");
        reordered.close(); reordered.close();
        require(closes.get() == 1, "close must propagate once");

        reads.set(0); closes.set(0);
        reordered = FilesListWitness.swapFirstPair(source(reads, closes));
        reordered.close();
        require(reads.get() == 0 && closes.get() == 1, "close before traversal");

        reads.set(0); closes.set(0);
        try (Stream<Path> all = FilesListWitness.swapFirstPair(source(reads, closes))) {
            require(all.collect(Collectors.toList()).equals(Arrays.asList(Path.of("b"), Path.of("a"),
                Path.of("c"), Path.of("d"))), "exact permutation and exhaustion");
        }
        require(reads.get() == 4 && closes.get() == 1, "complete traversal and close");

        UncheckedIOException marker = new UncheckedIOException(new IOException("controlled read error"));
        closes.set(0);
        Spliterator<Path> broken = new Spliterators.AbstractSpliterator<Path>(Long.MAX_VALUE, 0) {
            @Override
            public boolean tryAdvance(Consumer<? super Path> action) { throw marker; }
        };
        try (Stream<Path> stream = FilesListWitness.swapFirstPair(
                StreamSupport.stream(broken, false).onClose(closes::incrementAndGet))) {
            stream.findFirst();
            throw new AssertionError("expected read error");
        } catch (UncheckedIOException error) {
            require(error == marker, "read exception identity");
        }
        require(closes.get() == 1, "close after read error");
    }

    private static List<Path> list(Path dir) throws IOException {
        try (Stream<Path> stream = Files.list(dir)) { return stream.collect(Collectors.toList()); }
    }

    private static void directoryControls(Path parent, int size) throws IOException {
        Path dir = Files.createDirectory(parent.resolve("case-" + size));
        for (int i = 0; i < size; i++) Files.createFile(dir.resolve("entry-" + i));
        System.setProperty("fileslist.fixture.directory", dir.toString());
        List<Path> first = list(dir);
        List<Path> second = list(dir);
        List<Path> reversed = new ArrayList<>(first);
        if (size >= 2) Collections.swap(reversed, 0, 1);
        require(second.equals(reversed), "actual Files.list first-pair reversal, size " + size);
        List<Path> expected = new ArrayList<>();
        try (DirectoryStream<Path> entries = Files.newDirectoryStream(dir)) {
            entries.forEach(expected::add);
        }
        Collections.sort(expected); Collections.sort(first); Collections.sort(second);
        require(first.equals(expected) && second.equals(expected), "membership and sorted controls");
        for (Path entry : expected) Files.delete(entry);
        Files.delete(dir);
    }

    public static void main(String[] args) throws Exception {
        syntheticControls();
        Path parent = Files.createTempDirectory("files-list-controls-");
        try {
            for (int size : new int[]{0, 1, 2, 5}) directoryControls(parent, size);
            System.setProperty("fileslist.fixture.directory", parent.resolve("not-target").toString());
            require(list(parent).isEmpty(), "unmatched directory unchanged");
            System.setProperty("fileslist.fixture.directory", parent.toString());
            try {
                Files.list(parent.resolve("missing"));
                throw new AssertionError("expected missing-directory exception");
            } catch (java.nio.file.NoSuchFileException expected) { }
        } finally {
            Files.delete(parent);
        }
        System.out.println("PASS Files.list controls: lazy construction; bounded read-ahead; close propagation; "
            + "read exception; empty/singleton/two/five entries; exact permutation; membership; sorted control; "
            + "unmatched scope; missing-directory exception");
    }
}
