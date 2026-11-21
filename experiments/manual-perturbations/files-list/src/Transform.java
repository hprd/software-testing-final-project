import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassVisitor;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.MethodVisitor;
import org.objectweb.asm.Opcodes;

/** Adds one return hook to the selected runtime's Files.list(Path). */
public final class Transform {
    public static void main(String[] args) throws Exception {
        byte[] input;
        try (InputStream in = Object.class.getModule().getResourceAsStream("java/nio/file/Files.class")) {
            if (in == null) throw new IllegalStateException("Files.class missing");
            input = in.readAllBytes();
        }
        ClassWriter writer = new ClassWriter(0);
        int[] hooks = {0};
        new ClassReader(input).accept(new ClassVisitor(Opcodes.ASM9, writer) {
            @Override
            public MethodVisitor visitMethod(int access, String name, String descriptor,
                                             String signature, String[] exceptions) {
                MethodVisitor delegate = super.visitMethod(access, name, descriptor, signature, exceptions);
                if (!name.equals("list") || !descriptor.equals("(Ljava/nio/file/Path;)Ljava/util/stream/Stream;")) {
                    return delegate;
                }
                return new MethodVisitor(Opcodes.ASM9, delegate) {
                    @Override
                    public void visitInsn(int opcode) {
                        if (opcode == Opcodes.ARETURN) {
                            hooks[0]++;
                            super.visitVarInsn(Opcodes.ALOAD, 0);
                            super.visitMethodInsn(Opcodes.INVOKESTATIC, "java/nio/file/FilesListWitness", "wrap",
                                "(Ljava/util/stream/Stream;Ljava/nio/file/Path;)Ljava/util/stream/Stream;", false);
                        }
                        super.visitInsn(opcode);
                    }
                    @Override
                    public void visitMaxs(int stack, int locals) {
                        super.visitMaxs(stack + 1, locals);
                    }
                };
            }
        }, 0);
        if (hooks[0] != 1) throw new IllegalStateException("Expected exactly one list return; got " + hooks[0]);
        Path output = Path.of(args[0], "java/nio/file/Files.class");
        Files.createDirectories(output.getParent());
        Files.write(output, writer.toByteArray());
        System.out.println("TRANSFORM Files.list(Path): exactly one return hook");
    }
}
