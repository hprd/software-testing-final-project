import java.nio.file.*;
import org.objectweb.asm.*;
public class Transform {
 public static void main(String[] a) throws Exception {
  byte[] in=Object.class.getModule().getResourceAsStream("java/util/Hashtable.class").readAllBytes();
  ClassWriter w=new ClassWriter(0);
  new ClassReader(in).accept(new ClassVisitor(Opcodes.ASM9,w) {
   public MethodVisitor visitMethod(int access,String name,String desc,String sig,String[] exceptions) {
    MethodVisitor m=super.visitMethod(access,name,desc,sig,exceptions);
    if (!name.equals("keys") || !desc.equals("()Ljava/util/Enumeration;")) return m;
    return new MethodVisitor(Opcodes.ASM9,m) {
      public void visitInsn(int op) { if(op==Opcodes.ARETURN) { super.visitVarInsn(Opcodes.ALOAD,0); super.visitMethodInsn(Opcodes.INVOKESTATIC,"java/util/HashtableWitness","reverseTarget","(Ljava/util/Enumeration;Ljava/util/Hashtable;)Ljava/util/Enumeration;",false); } super.visitInsn(op); }
      public void visitMaxs(int stack,int locals) { super.visitMaxs(stack+1,locals); }
    };
   }
  },0);
  Path out=Paths.get(a[0],"java/util/Hashtable.class"); Files.createDirectories(out.getParent()); Files.write(out,w.toByteArray());
 }
}
