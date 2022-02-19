import lark
import itertools
from collections import defaultdict as dd

preorder = (
    'class_',
    'method',
    'and_exp',
    'or_exp',
    'if_stmt',
    'while_lp'
)

#generate assembly code from the parse tree
class Generator(lark.visitors.Visitor_Recursive):
    def __init__(self, classes, types):
        #store the code array and types table
        super().__init__()
        self.classes_ = classes
        self.current_class = None
        self.current_method = None
        self.types = types
        self.variables = {} #stores names and types of local variables
        self.labels = dd(itertools.count) #stores count of label prefixes
    def emit(self, line, tab=True):
        #emits a line of code to the output array
        #adds a tab to the beginning by default
        if tab:
            line = '\t' + line
        self.current_method['code'].append(line)
    def label(self, prefix):
        #generates a unique label name with the given prefix
        num = next(self.labels[prefix]) #get current number for given prefix
        return f'{prefix}_{num}'
    def visit(self, tree):
        #some nodes need to be visited before their children
        #if this node is such a node, visit it directly
        #the node's method may visit its children
        if tree.data in preorder:
            getattr(self, tree.data)(tree)
        else:
            #most expressions are traversed postorder
            return super().visit(tree)
    def class_(self, tree):
        name = str(tree.children[0].children[0])
        sup = str(tree.children[0].children[2] or 'Obj')
        obj = {
            'name': name,
            'super': sup,
            'methods': [],
            'fields': {}
        }
        self.current_class = obj
        self.classes_.append(obj)
        for method in tree.children[1].children[0].children:
            self.visit(method)
    def method(self, tree):
        name = str(tree.children[0])
        args = tree.children[1]
        obj = {
            'name': name,
            'args': [str(arg.children[0]) for arg in args.children],
            'code': []
        }
        self.current_class['methods'].append(obj)
        self.current_method = obj
        for child in tree.children[3].children:
            self.visit(child)
    def lit_number(self, tree):
        #push an integer onto the stack
        self.emit('const %s' % tree.children[0])
    def lit_true(self, tree):
        #push a boolean onto the stack
        self.emit('const true')
    def lit_false(self, tree):
        #push a boolean onto the stack
        self.emit('const false')
    def lit_nothing(self, tree):
        #push a nothing onto the stack
        self.emit('const nothing')
    def lit_string(self, tree):
        #push a string onto the stack
        self.emit('const %s' % tree.children[0])
    def var(self, tree):
        #load a local variable onto the stack
        self.emit('load %s' % tree.children[0])
    def assign(self, tree):
        #store the top value on the stack into a local variable
        name = tree.children[0]
        if tree.children[1] is not None:
            type = tree.children[1]
        else:
            type = tree.type
        #map the variable name to the type of the value
        self.variables[name] = type
        #emit a store instruction
        self.emit('store %s' % name)
    def m_call(self, tree):
        #emit a method call command and possibly a roll
        m_name = str(tree.children[1])
        #functions need to roll so that the receiver
        #is the first thing popped off the stack
        num_ops = len(tree.children[2].children)
        if num_ops: #don't roll for functions with no arguments
            self.emit('roll %d' % num_ops)
        left_type = tree.children[0].type
        #emit a method call of the correct type
        self.emit('call %s:%s' % (left_type, tree.children[1]))
    def raw_rexp(self, tree):
        #if a statement is just a right_expression, the value of the expression
        #stays on the stack but is not used, so it can be popped
        self.emit('pop')
    def and_exp(self, tree):
        left, right = tree.children
        #generate assembly for first expression, which will always run
        self.visit(left)
        #generate unique label names
        false_label = self.label('and')
        join_label = self.label('and')
        #if the first expression evaluates to false, jump to join point
        self.emit('jump_ifnot %s' % false_label)
        #generate assembly for second expression
        #this will only run if the first expression evaluated to true
        self.visit(right)
        #if the second expression evaluates to false, jump to join point
        self.emit('jump_ifnot %s' % false_label)
        #if neither jump was taken, push true as the result
        self.emit('const true')
        #skip past the join point
        self.emit('jump %s' % join_label)
        #join point: execution will come here if either expression is false
        self.emit('%s:' % false_label, False)
        #if either jump was taken, push false as the result
        self.emit('const false')
        #and expression is over - join point
        self.emit('%s:' % join_label, False)
    def or_exp(self, tree):
        left, right = tree.children
        #generate assembly for first expression, which will always run
        self.visit(left)
        #generate unique label names
        true_label = self.label('or')
        join_label = self.label('or')
        #if the first expression evaluates to true, jump to join point
        self.emit('jump_if %s' % true_label)
        #generate assembly for second expression
        #this will only run if the first expression evaluated to false
        self.visit(right)
        #if the second expression evaluates to true, jump to join point
        self.emit('jump_if %s' % true_label)
        #if neither jump was taken, push false as the result
        self.emit('const false')
        #skip past the join point
        self.emit('jump %s' % join_label)
        #join point: execution will come here if either expression is true
        self.emit('%s:' % true_label, False)
        #if either jump was taken, push true as the result
        self.emit('const true')
        #or expression is over - join point
        self.emit('%s:' % join_label, False)
    def if_stmt(self, tree):
        #unpack children nodes for convenience
        if_cond, if_block, elifs, _else = tree.children

        join_label = self.label('join') #generate join label - emitted at end
        #holds all labels used in this block
        #must be pregenerated so that future labels can be accessed
        labels = []
        for child in elifs.children:
            labels.append(self.label('elif')) #add "elif" for each elif block
        if _else.children:
            labels.append(self.label('else')) #if else block exists, add "else"

        #unconditionally evaluate the if statement's condition
        self.visit(if_cond)
        #emit the correct label to jump to if the condition was false
        if not labels:
            #if the if statement is alone, jump to the join point
            self.emit('jump_ifnot %s' % join_label)
        else:
            #if the if statement has friends, jump to the next condition
            self.emit('jump_ifnot %s' % labels[0])
        #if condition was true, execute the block
        self.visit(if_block)
        if labels:
            #jump past elif/else blocks to the join point
            self.emit('jump %s' % join_label)

        label_index = 0 #used to get current/next labels
        #generate code for elif blocks, if there are any
        for _elif in elifs.children:
            #unpack condition/block for convenience
            elif_cond, elif_block = _elif.children
            #get label that points to this block
            current_label = labels[label_index]
            label_index += 1
            #get label that will be jumped to if this block doesn't execute
            next_label = join_label if label_index == len(labels) else labels[label_index]

            #emit this block's label
            self.emit('%s:' % current_label, False)
            #evaluate the elif's condition
            self.visit(elif_cond)
            #jump to next block or join point if condition was false
            self.emit('jump_ifnot %s' % next_label)
            #execute block if condition was true
            self.visit(elif_block)
            #only jump to join if there is a block in between here and there
            if next_label != join_label:
                #jump past rest of the blocks after execution
                self.emit('jump %s' % join_label)

        #generate code for else block, if it exists
        if _else.children:
            #else label is always the last in labels
            else_label = labels[-1]
            #emit this block's label
            self.emit('%s:' % else_label, False)
            else_block = _else.children[0]
            #execute the else block
            self.visit(else_block)

        #emit the join label - this point will always be reached
        self.emit('%s:' % join_label, False)
    def while_lp(self, tree):
        #unpack children nodes for convenience
        condition, block = tree.children
        #generate unique labels for block and condition
        block_label = self.label('while_block')
        cond_label = self.label('while_cond')
        #unconditionally jump to condition check
        self.emit('jump %s' % cond_label)
        #emit label for start of block
        self.emit('%s:' % block_label, False)
        #generate code for block
        self.visit(block)
        #emit label for condition check
        self.emit('%s:' % cond_label, False)
        #generate code for condition check
        self.visit(condition)
        #if condition evaluates to true, jump to beginning of block
        self.emit('jump_if %s' % block_label)

#outputs assembly code to given stream
def generate_code(name, variables, code, out):
    emit = lambda s: print(s, file=out) #convenience method
    #emit header common to all files
    emit('.class %s:Obj\n\n.method $constructor' % name)
    if variables:
        #emit list of local variables separated by commas
        emit('.local %s' % ','.join(i for i in variables))
    emit('\tenter')
    #emit each line, indented by one tab
    for line in code:
        emit(line)
    #push return value of constructor
    emit('\tconst nothing')
    #return, popping zero arguments
    emit('\treturn 0')

#generates assembly file for the given class object
def generate_file(class_):
    name = class_['name']
    sup = class_['super']
    methods = class_['methods']
    fields = class_['fields']
    filename = name + '.asm'
    with open(filename, 'w') as f:
        f.write('.class %s:%s\n' % (name, sup))
        for field in fields:
            f.write('.field %s\n' % field)
        f.write('\n')
        for method in methods:
            m_name = method['name']
            args = method['args']
            code = method['code']
            f.write('.method %s\n' % m_name)
            if args:
                s = ','.join(args)
                f.write('.args %s\n' % s)
            for line in code:
                f.write(line + '\n')
            f.write('\n')
